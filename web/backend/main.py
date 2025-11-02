from pathlib import Path
import shutil
import subprocess
import yaml
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import uuid

app = FastAPI(title="vdesk-backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
THIS_FILE = Path(__file__).resolve()
WEB_ROOT = THIS_FILE.parent.parent  # web/
PROJECT_ROOT = WEB_ROOT.parent  # project root (vdesk)
CONTAINERS_DIR = WEB_ROOT / "containers"
TEMPLATE_COMPOSE = PROJECT_ROOT / "scripts" / "docker-compose.yml.example"

CONTAINERS_DIR.mkdir(exist_ok=True)

# Setup logs directory and rotating logger
LOG_DIR = WEB_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "commands.log"

# configure rotating file handler (5MB per file, keep 7 backups)
handler = RotatingFileHandler(str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=7)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# avoid adding duplicate handlers if module reloaded
if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(LOG_FILE) for h in logger.handlers):
    logger.addHandler(handler)
# also log to console
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

# Models
class ContainerCreate(BaseModel):
    name: str = Field(..., description="6-digit user name")
    image: str
    cpus: int = Field(..., ge=1, le=32)
    memory: str
    gpus: List[int] = []
    port: int = 0
    swap: Optional[str] = None
    root_password: Optional[str] = None

class ContainerModify(BaseModel):
    memory: Optional[str]
    gpus: Optional[List[int]]
    swap: Optional[str]
    root_password: Optional[str]

class ContainerInfo(BaseModel):
    name: str
    image: Optional[str] = None
    memory: Optional[str] = None
    cpus: Optional[str] = None
    gpus: Optional[List[int]] = None
    port: Optional[int] = None
    swap: Optional[str] = None
    root_password: Optional[str] = None
    state: Optional[str] = None

# Helpers

def load_compose(path: Path):
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_compose(path: Path, data):
    with path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def run_compose(compose_path: Path, args: List[str]):
    cmd = ["docker", "compose", "-f", str(compose_path)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # Log command output to the log file
        try:
            logging.info("CMD: %s RETURN: %s", ' '.join(cmd), proc.returncode)
            if proc.stdout:
                logging.info("STDOUT: %s", proc.stdout)
            if proc.stderr:
                logging.info("STDERR: %s", proc.stderr)
        except Exception:
            pass
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except FileNotFoundError as e:
        logging.error("CMD FAILED: %s ERROR: %s", ' '.join(cmd), str(e))
        return {"returncode": 127, "stdout": "", "stderr": str(e)}


def parse_compose_info(compose_data) -> ContainerInfo:
    info = ContainerInfo(name="")
    try:
        svc = compose_data.get("services", {}).get("my_ws", {})
        info.image = svc.get("image")
        ports = svc.get("ports", [])
        if ports:
            # assume 'HOST:CONTAINER' format
            first = ports[0]
            try:
                host = int(str(first).split(":")[0])
                info.port = host
            except Exception:
                pass
        deploy = svc.get("deploy", {})
        limits = deploy.get("resources", {}).get("limits", {})
        info.memory = limits.get("memory")
        info.cpus = limits.get("cpus")
        reservations = deploy.get("resources", {}).get("reservations", {})
        devices = reservations.get("devices", [])
        if devices and isinstance(devices, list):
            # device_ids may be under first device
            info.gpus = devices[0].get("device_ids") if devices[0].get("device_ids") is not None else devices
        # environment
        env = svc.get("environment", {})
        info.root_password = env.get("ROOT_PASSWORD")
        info.swap = env.get("SWAP_SIZE")
    except Exception:
        pass
    return info

def _docker_ps_map():
    """Return a list of tuples (name, status) from `docker ps -a`."""
    try:
        proc = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}|||{{.Status}}"], capture_output=True, text=True, check=False)
        # log output
        try:
            logging.info("CMD: docker ps -a --format '{{.Names}}|||{{.Status}}' RETURN: %s", proc.returncode)
            if proc.stdout:
                logging.info("STDOUT: %s", proc.stdout)
            if proc.stderr:
                logging.info("STDERR: %s", proc.stderr)
        except Exception:
            pass
        out = proc.stdout or ""
    except FileNotFoundError:
        logging.error("docker command not found when running docker ps -a")
        return []
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    entries = []
    for line in lines:
        try:
            name, status = line.split('|||', 1)
            entries.append((name, status))
        except ValueError:
            continue
    return entries

def compute_host_port_from_name(name: str) -> int:
    """Compute host port from 6-digit name.
    First digit = (digit1 + digit2) % 6
    Last 4 digits = last 4 digits of name
    Returns integer port.
    """
    if not (isinstance(name, str) and name.isdigit() and len(name) == 6):
        raise ValueError("name must be 6 digits")
    d1 = int(name[0])
    d2 = int(name[1])
    first_digit = (d1 + d2) % 6
    last4 = name[-4:]
    port_str = f"{first_digit}{last4}"
    try:
        port = int(port_str)
    except ValueError:
        raise ValueError("computed port invalid")
    if port < 1 or port > 65535:
        raise ValueError("computed port out of range")
    return port

# Endpoints

@app.get("/api/images")
def list_images():
    # Simple static list; in a real system this might query a registry
    return [
        "10.233.0.132:8000/hdm/ros2-humble-cu12.4.1-nomachine-priviledged:1.0",
        "10.233.0.132:8000/ubuntu:22.04",
        "10.233.0.132:8000/ubuntu:20.04",
        "nvidia/cuda:12.1.0-base-ubuntu22.04",
    ]

@app.post("/api/containers")
def create_container(payload: ContainerCreate):
    # validate name
    if not (payload.name.isdigit() and len(payload.name) == 6):
        raise HTTPException(status_code=400, detail="name must be 6 digits")
    # compute host port from name per README rules
    try:
        host_port = compute_host_port_from_name(payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    dest = CONTAINERS_DIR / payload.name
    if dest.exists():
        raise HTTPException(status_code=400, detail="container already exists")
    if not TEMPLATE_COMPOSE.exists():
        raise HTTPException(status_code=500, detail=str(TEMPLATE_COMPOSE) + " not found")
    dest.mkdir(parents=True)
    compose_path = dest / "docker-compose.yml"
    shutil.copy2(TEMPLATE_COMPOSE, compose_path)

    data = load_compose(compose_path)
    if data is None:
        raise HTTPException(status_code=500, detail="failed to load compose template")

    svc = data.setdefault("services", {}).setdefault("my_ws", {})
    # set image
    svc["image"] = payload.image
    # determine container-side port from template if present
    container_port = None
    ports_def = svc.get("ports")
    if ports_def and isinstance(ports_def, list) and len(ports_def) > 0:
        first = ports_def[0]
        # support short string 'HOST:CONTAINER' or 'HOST:CONTAINER/proto'
        if isinstance(first, str):
            try:
                right = first.split(":", 1)[1]
                container_port = right.split("/")[0]
            except Exception:
                container_port = None
        elif isinstance(first, dict):
            # long syntax: { published: 14000, target: 4000 }
            container_port = str(first.get("target") or first.get("container") or first.get("to") or "")
            if container_port == "":
                container_port = None
    # fallback default container port
    if not container_port:
        container_port = "22"
    # set ports mapping using computed host port -> template container port
    svc["ports"] = [f"{host_port}:{container_port}"]
    # ensure deploy/resources structure
    deploy = svc.setdefault("deploy", {})
    resources = deploy.setdefault("resources", {})
    limits = resources.setdefault("limits", {})
    limits["memory"] = payload.memory
    limits["cpus"] = str(payload.cpus)
    reservations = resources.setdefault("reservations", {})
    # devices list
    if payload.gpus:
        # store devices in the full expected structure for docker-compose
        reservations["devices"] = [{
            "driver": "nvidia",
            "device_ids": [str(x) for x in payload.gpus],
            "capabilities": ["gpu"],
        }]
    # environment
    env = svc.setdefault("environment", {})
    if payload.root_password:
        env["ROOT_PASSWORD"] = payload.root_password
    if payload.swap:
        env["SWAP_SIZE"] = payload.swap

    save_compose(compose_path, data)

    # start container
    res = run_compose(compose_path, ["up", "-d"])
    return {"compose_result": res}

@app.get("/api/containers")
def list_containers():
    results = []
    for p in sorted(CONTAINERS_DIR.iterdir()):
        if not p.is_dir():
            continue
        compose_path = p / "docker-compose.yml"
        if not compose_path.exists():
            continue
        data = load_compose(compose_path)
        if data is None:
            continue
        info = parse_compose_info(data)
        info.name = p.name
        # determine state from `docker ps -a` STATUS field
        state = None
        for cname, cstatus in _docker_ps_map():
            if p.name in cname:
                state = cstatus
                break
        info.state = state or "not running"
        results.append(info)
    return results

@app.put("/api/containers/{name}")
def modify_container(name: str, payload: ContainerModify):
    path = CONTAINERS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    compose_path = path / "docker-compose.yml"
    data = load_compose(compose_path)
    if data is None:
        raise HTTPException(status_code=500, detail="invalid compose")
    svc = data.setdefault("services", {}).setdefault("my_ws", {})
    deploy = svc.setdefault("deploy", {})
    resources = deploy.setdefault("resources", {})
    limits = resources.setdefault("limits", {})
    reservations = resources.setdefault("reservations", {})
    if payload.memory:
        limits["memory"] = payload.memory
    if payload.gpus is not None:
        if payload.gpus:
            reservations["devices"] = [{
                "driver": "nvidia",
                "device_ids": [str(x) for x in payload.gpus],
                "capabilities": ["gpu"],
            }]
        else:
            reservations.pop("devices", None)
    env = svc.setdefault("environment", {})
    if payload.root_password is not None:
        env["ROOT_PASSWORD"] = payload.root_password
    if payload.swap is not None:
        env["SWAP_SIZE"] = payload.swap

    save_compose(compose_path, data)

    # restart to apply
    res = run_compose(compose_path, ["up", "-d", "--force-recreate"])
    return {"compose_result": res}

@app.post("/api/containers/{name}/action")
def container_action(name: str, action: str):
    path = CONTAINERS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    compose_path = path / "docker-compose.yml"
    if action not in ("start", "stop", "restart", "delete"):
        raise HTTPException(status_code=400, detail="invalid action")
    if action == "start":
        res = run_compose(compose_path, ["up", "-d"])
        return {"result": res}
    if action == "stop":
        res = run_compose(compose_path, ["down"])
        return {"result": res}
    if action == "restart":
        run_compose(compose_path, ["down"])
        res = run_compose(compose_path, ["up", "-d"])
        return {"result": res}
    if action == "delete":
        run_compose(compose_path, ["down"])
        # remove folder
        try:
            shutil.rmtree(path)
            return {"result": "deleted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
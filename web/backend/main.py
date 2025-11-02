from pathlib import Path
import shutil
import subprocess
import yaml
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

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

# Models
class ContainerCreate(BaseModel):
    name: str = Field(..., description="6-digit user name")
    image: str
    cpus: int = Field(..., ge=1, le=32)
    memory: str
    gpus: List[int] = []
    port: int
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
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except FileNotFoundError as e:
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

# Endpoints

@app.get("/api/images")
def list_images():
    # Simple static list; in a real system this might query a registry
    return [
        "ubuntu:22.04",
        "python:3.11-slim",
        "nvidia/cuda:12.1.0-base-ubuntu22.04",
    ]

@app.post("/api/containers")
def create_container(payload: ContainerCreate):
    # validate name
    if not (payload.name.isdigit() and len(payload.name) == 6):
        raise HTTPException(status_code=400, detail="name must be 6 digits")
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
    # set ports - assume container uses 22 or 8888; we map host port to container 22 by default
    svc["ports"] = [f"{payload.port}:22"]
    # ensure deploy/resources structure
    deploy = svc.setdefault("deploy", {})
    resources = deploy.setdefault("resources", {})
    limits = resources.setdefault("limits", {})
    limits["memory"] = payload.memory
    limits["cpus"] = str(payload.cpus)
    reservations = resources.setdefault("reservations", {})
    # devices list
    if payload.gpus:
        reservations["devices"] = [{"device_ids": payload.gpus}]
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
        # get container state using docker compose ps
        ps = run_compose(compose_path, ["ps", "--format", "json"])  # may not be supported in compose v2
        state = None
        if ps and ps.get("stdout"):
            out = ps["stdout"].strip()
            if out:
                # best effort: if any service listed, consider running
                state = "running"
        info.state = state or "unknown"
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
            reservations["devices"] = [{"device_ids": payload.gpus}]
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
from pathlib import Path
import shutil
import subprocess
import yaml
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi import Request, Response
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import uuid
import time
from typing import Dict
import os
import json
import bcrypt
import secrets

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
    shm_size: Optional[str] = None
    gpus: List[int] = []
    port: int = 0
    swap: Optional[str] = None
    root_password: Optional[str] = None
    comment: Optional[str] = None

class ContainerModify(BaseModel):
    memory: Optional[str]
    shm_size: Optional[str]
    gpus: Optional[List[int]]
    swap: Optional[str]
    root_password: Optional[str]
    comment: Optional[str]

class ContainerInfo(BaseModel):
    name: str
    image: Optional[str] = None
    memory: Optional[str] = None
    shm_size: Optional[str] = None
    cpus: Optional[str] = None
    gpus: Optional[List[int]] = None
    port: Optional[int] = None
    swap: Optional[str] = None
    root_password: Optional[str] = None
    comment: Optional[str] = None
    state: Optional[str] = None

class ChangePasswordModel(BaseModel):
    old_password: str
    new_password: str


# Helpers

def load_compose(path: Path):
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_compose(path: Path, data, comment: Optional[str] = None):
    """Write compose YAML to file. If comment is provided, write a top-line comment
    `# comment: ...`. If comment is None, preserve an existing top comment line
    starting with `# comment:` if present.
    """
    comment_line = None
    if comment is not None:
        comment_line = f"# comment: {comment}\n"
    else:
        # try to preserve existing comment if present
        if path.exists():
            try:
                with path.open() as f:
                    first = f.readline()
                    if first.startswith("# comment:"):
                        comment_line = first
            except Exception:
                comment_line = None
    with path.open("w") as f:
        if comment_line:
            f.write(comment_line)
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
        # shm_size may be present
        info.shm_size = svc.get("shm_size")
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
        # environment in docker-compose may be a dict or a list of 'KEY=VALUE' strings
        root_pw = None
        swap_val = None
        if isinstance(env, dict):
            root_pw = env.get("ROOTPASSWORD")
            swap_val = env.get("SWAP_SIZE")
        elif isinstance(env, list):
            for item in env:
                try:
                    if not isinstance(item, str):
                        continue
                    k, v = item.split("=", 1)
                    if k in ("ROOTPASSWORD"):
                        root_pw = v
                    if k == "SWAP_SIZE":
                        swap_val = v
                except Exception:
                    continue
        info.root_password = root_pw
        info.swap = swap_val
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

def get_host_resources():
    """Return host resources: cpu count, total memory in bytes, gpus list of dicts {id,name}."""
    # CPUs
    cpus = os.cpu_count() or 1
    # Memory: try /proc/meminfo
    mem_bytes = None
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    parts = line.split()
                    # value is in kB
                    mem_kb = int(parts[1])
                    mem_bytes = mem_kb * 1024
                    break
    except Exception:
        mem_bytes = None
    # fallback using 'free -b'
    if mem_bytes is None:
        try:
            proc = subprocess.run(['free', '-b'], capture_output=True, text=True, check=False)
            if proc.stdout:
                # second line has Mem: <total> ...
                lines = proc.stdout.splitlines()
                if len(lines) >= 2:
                    vals = lines[1].split()
                    if len(vals) >= 2:
                        mem_bytes = int(vals[1])
        except Exception:
            mem_bytes = None
    # GPUs: try nvidia-smi to get index and name
    gpus = []
    try:
        proc = subprocess.run(['nvidia-smi', '--query-gpu=index,name', '--format=csv,noheader'], capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                # CSV with two fields: index, name
                parts = [p.strip() for p in line.split(',', 1)]
                if len(parts) == 2:
                    gid, gname = parts
                else:
                    gid = parts[0]
                    gname = ''
                gpus.append({'id': gid, 'name': gname})
    except FileNotFoundError:
        # nvidia-smi not present
        gpus = []
    except Exception:
        gpus = []
    return {'cpus': cpus, 'memory_bytes': mem_bytes, 'gpus': gpus}


@app.get('/api/host')
def host_info():
    """Return host resource information."""
    try:
        info = get_host_resources()
        return info
    except Exception as e:
        logging.exception('failed to get host resources: %s', e)
        raise HTTPException(status_code=500, detail='failed to get host resources')

# Endpoints

@app.get("/api/images")
def list_images():
    # Use environment variable for registry URL, fallback to default if not set
    registry_url = os.environ.get("VDESK_REGISTRY_URL", "10.233.0.132:8000/hdm/")
    return [
        "ubuntu:20.04",
        "ubuntu:22.04",
        f"{registry_url}ubuntu-desktop-nomachine-cuda:22.04-cu12.4.1",
        f"{registry_url}ros2-humble-cu12.4.1-nomachine-priviledged:1.0",
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
    # set shared memory size if provided
    if payload.shm_size:
        svc["shm_size"] = payload.shm_size
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
    # support both dict and list formats for environment in the compose template
    env = svc.get("environment")
    # generate a strong random root password if not provided
    if payload.root_password:
        root_pw = payload.root_password
    else:
        # generate a URL-safe password of approximately 14-15 characters
        root_pw = secrets.token_urlsafe(11)

    # use the module-level helper `set_env_key_in_list` (defined earlier)

    if isinstance(env, list):
        set_env_key_in_list(env, "ROOTPASSWORD", root_pw)
        if payload.swap:
            set_env_key_in_list(env, "SWAP_SIZE", payload.swap)
    elif isinstance(env, dict):
        env["ROOTPASSWORD"] = root_pw
        if payload.swap:
            env["SWAP_SIZE"] = payload.swap
    else:
        # not present or unexpected type: create dict
        new_env = {"ROOTPASSWORD": root_pw}
        if payload.swap:
            new_env["SWAP_SIZE"] = payload.swap
        svc["environment"] = new_env

    save_compose(compose_path, data, payload.comment)

    # start container
    res = run_compose(compose_path, ["up", "-d"])
    # run patch script to adjust the freshly created container
    patch_script = PROJECT_ROOT / "scripts" / "patches.sh"
    patch_result = None
    try:
        # poll for the container to appear (timeout 30s)
        # expected container name format: <project>-<service>-1 where project is the folder name (payload.name)
        container_name = f"{payload.name}-my_ws-1"
        found = False
        start = time.time()
        timeout = 30
        interval = 1
        while time.time() - start < timeout:
            try:
                for cname, _ in _docker_ps_map():
                    if cname == container_name or container_name in cname:
                        found = True
                        break
            except Exception:
                found = False
            if found:
                logging.info("Container %s appeared after %.1fs", container_name, time.time() - start)
                break
            time.sleep(interval)
        if not found:
            logging.warning("Container %s did not appear within %s seconds, proceeding to run patch script anyway", container_name, timeout)
        proc = subprocess.run(["/bin/bash", str(patch_script), container_name], capture_output=True, text=True, check=False)
        logging.info("PATCH CMD: %s %s RETURN: %s", str(patch_script), container_name, proc.returncode)
        if proc.stdout:
            logging.info("PATCH STDOUT: %s", proc.stdout)
        if proc.stderr:
            logging.info("PATCH STDERR: %s", proc.stderr)
        patch_result = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except FileNotFoundError as e:
        logging.error("PATCH SCRIPT NOT FOUND: %s", str(e))
        patch_result = {"returncode": 127, "stdout": "", "stderr": str(e)}
    except Exception as e:
        logging.exception("error running patch script: %s", e)
        patch_result = {"returncode": 1, "stdout": "", "stderr": str(e)}
    return {"compose_result": res, "patch_result": patch_result, "root_password": root_pw}

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
        # read optional top comment line from compose file
        try:
            with compose_path.open() as f:
                first = f.readline().strip()
                if first.startswith("# comment:"):
                    info.comment = first[len("# comment:"):].strip()
        except Exception:
            pass
        # determine state from `docker ps -a` STATUS field
        state = None
        for cname, cstatus in _docker_ps_map():
            if p.name in cname:
                state = cstatus
                break
        info.state = state or "idle"
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
    # update shm_size when modifying
    if payload.shm_size is not None:
        if payload.shm_size:
            svc["shm_size"] = payload.shm_size
        else:
            svc.pop("shm_size", None)
    env = svc.get("environment")
    # handle both dict and list formats for environment
    if payload.root_password is not None:
        if isinstance(env, list):
            set_env_key_in_list(env, "ROOTPASSWORD", payload.root_password)
        elif isinstance(env, dict):
            env["ROOTPASSWORD"] = payload.root_password
        else:
            # not present or unexpected type: create dict
            svc["environment"] = {"ROOTPASSWORD": payload.root_password}
            env = svc["environment"]
    if payload.swap is not None:
        if isinstance(env, list):
            set_env_key_in_list(env, "SWAP_SIZE", payload.swap)
        elif isinstance(env, dict):
            env["SWAP_SIZE"] = payload.swap
        else:
            # not present or unexpected type: create dict
            svc["environment"] = {"SWAP_SIZE": payload.swap}
            env = svc["environment"]

    # preserve or update top comment when saving
    save_compose(compose_path, data, payload.comment if getattr(payload, 'comment', None) is not None else None)

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

# Simple in-memory auth (demo). Replace with real auth in production.
USERS_FILE = WEB_ROOT / "users.json"


def load_users():
    """Load users from USERS_FILE. Returns a dict username -> hashed_password_str.
    If the file does not exist, create a default admin user with password 'admin' hashed.
    """
    try:
        if USERS_FILE.exists():
            with USERS_FILE.open() as f:
                data = json.load(f)
                # ensure keys and values are strings
                return {str(k): str(v) for k, v in data.items()}
        # create default admin user
        default = {}
        hashed = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        default["admin"] = hashed
        try:
            with USERS_FILE.open("w") as f:
                json.dump(default, f)
        except Exception:
            logging.exception("failed to write default users file")
        return default
    except Exception:
        logging.exception("failed to load users file")
        return {}


def save_users(users: dict):
    try:
        with USERS_FILE.open("w") as f:
            json.dump(users, f)
    except Exception:
        logging.exception("failed to save users file")


def set_user_password(username: str, password: str):
    users = load_users()
    users[username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    save_users(users)


# load users into memory; authentication checks will read from USERS for simplicity
USERS: Dict[str, str] = load_users()
TOKENS: Dict[str, dict] = {}  # token -> {user, exp}


def _create_token(username: str, ttl: int = 60 * 60 * 12):
    token = uuid.uuid4().hex
    TOKENS[token] = {"user": username, "exp": time.time() + ttl}
    return token


def _validate_token(token: str):
    entry = TOKENS.get(token)
    if not entry:
        return None
    if entry.get("exp", 0) < time.time():
        TOKENS.pop(token, None)
        return None
    return entry.get("user")


@app.post("/api/login")
def api_login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    expected = USERS.get(username)
    # expected is a bcrypt hash string; verify
    try:
        if expected is None or not bcrypt.checkpw(password.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="invalid credentials")
    except ValueError:
        # invalid hash format
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = _create_token(username)
    return {"token": token, "user": username}


@app.post("/api/logout")
def api_logout(payload: dict):
    token = payload.get("token")
    if token:
        TOKENS.pop(token, None)
    return {"result": "ok"}


@app.post('/api/change-password')
def change_password(payload: ChangePasswordModel, request: Request):
    """Change the password for the authenticated user.
    Requires Authorization: Bearer <token>. Verifies the provided old_password
    then sets the new password (hashed) and invalidates existing tokens for
    that user so they must re-login.
    """
    global USERS
    username = getattr(request.state, 'user', None)
    if not username:
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload.old_password or not payload.new_password:
        raise HTTPException(status_code=400, detail='old_password and new_password required')
    current_hash = USERS.get(username)
    try:
        if current_hash is None or not bcrypt.checkpw(payload.old_password.encode(), current_hash.encode()):
            raise HTTPException(status_code=401, detail='invalid current password')
    except ValueError:
        # invalid hash format
        raise HTTPException(status_code=401, detail='invalid current password')

    # update stored password (this writes users.json)
    try:
        set_user_password(username, payload.new_password)
    except Exception as e:
        logging.exception('failed to set new password: %s', e)
        raise HTTPException(status_code=500, detail='failed to set new password')

    # reload USERS into memory
    # global USERS
    USERS = load_users()

    # invalidate any existing tokens for this user
    try:
        for t, entry in list(TOKENS.items()):
            if entry.get('user') == username:
                TOKENS.pop(t, None)
    except Exception:
        logging.exception('failed to invalidate tokens for user %s', username)

    return {'result': 'ok', 'message': 'password changed; please re-login'}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # allow public paths
    public_prefixes = ("/api/login", "/api/images", "/api/openapi.json", "/docs", "/favicon.ico", "/static", "/api/host")
    path = request.url.path
    for p in public_prefixes:
        if path.startswith(p):
            return await call_next(request)
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return Response(status_code=401, content="unauthorized")
    token = auth.split(None, 1)[1]
    user = _validate_token(token)
    if not user:
        return Response(status_code=401, content="unauthorized")
    # attach user info to request.state if handlers need it
    request.state.user = user
    return await call_next(request)


def set_env_key_in_list(env_list, key, val):
    """Update or append an environment entry in a docker-compose 'environment' list.
    env_list: list of strings like 'KEY=VALUE'
    Modifies env_list in place.
    """
    if not isinstance(env_list, list):
        return
    updated = False
    for i, item in enumerate(env_list):
        if not isinstance(item, str):
            continue
        try:
            k = item.split("=", 1)[0]
        except Exception:
            continue
        if k == key:
            env_list[i] = f"{key}={val}"
            updated = True
            break
    if not updated:
        env_list.append(f"{key}={val}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
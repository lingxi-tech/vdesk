import os
import subprocess
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
CONTAINERS_DB = os.path.join(os.path.dirname(__file__), "containers.db")

engine = create_engine(f"sqlite:///{CONTAINERS_DB}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ContainerModel(Base):
    __tablename__ = "containers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    image = Column(String, nullable=True)
    memory_size = Column(String, nullable=True)
    gpu_ids = Column(String, nullable=True)  # JSON list stored as text
    swap_size = Column(String, nullable=True)
    root_password = Column(String, nullable=True)
    state = Column(String, nullable=True)
    dir_path = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="vdesk container manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContainerCreate(BaseModel):
    name: str
    image: Optional[str] = None
    memory_size: Optional[str] = "16g"
    gpu_ids: Optional[List[int]] = []
    swap_size: Optional[str] = "32g"
    root_password: Optional[str] = None

class ContainerUpdate(BaseModel):
    key: str
    value: str

class ContainerOut(BaseModel):
    name: str
    image: Optional[str]
    memory_size: Optional[str]
    gpu_ids: Optional[List[int]]
    swap_size: Optional[str]
    root_password: Optional[str]
    state: Optional[str]

@app.get("/containers", response_model=List[ContainerOut])
def list_containers():
    db = SessionLocal()
    try:
        rows = db.query(ContainerModel).all()
        out = []
        for r in rows:
            gpu_ids = json.loads(r.gpu_ids) if r.gpu_ids else []
            out.append(ContainerOut(
                name=r.name,
                image=r.image,
                memory_size=r.memory_size,
                gpu_ids=gpu_ids,
                swap_size=r.swap_size,
                root_password=r.root_password,
                state=r.state,
            ))
        return out
    finally:
        db.close()

@app.post("/containers", response_model=ContainerOut)
def create_container(spec: ContainerCreate):
    db = SessionLocal()
    try:
        exists = db.query(ContainerModel).filter_by(name=spec.name).first()
        if exists:
            raise HTTPException(status_code=400, detail="container with this name already exists")
        # call container-management.sh to create folder and bring up container
        project_root = BASE_DIR  # project root contains scripts
        cmd = ["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", spec.name, "--command", "reset_compose"]
        subprocess.run(cmd, cwd=project_root, check=False)
        # update memory/password/image if provided
        if spec.memory_size:
            subprocess.run(["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", spec.name, "--command", "update_memory", spec.memory_size], cwd=project_root, check=False)
        if spec.root_password:
            subprocess.run(["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", spec.name, "--command", "update_password", spec.root_password], cwd=project_root, check=False)
        if spec.image:
            subprocess.run(["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", spec.name, "--command", "change_image", spec.image], cwd=project_root, check=False)
        # bring up the container
        subprocess.run(["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", spec.name, "--command", "container_up"], cwd=project_root, check=False)
        # persist
        model = ContainerModel(
            name=spec.name,
            image=spec.image,
            memory_size=spec.memory_size,
            gpu_ids=json.dumps(spec.gpu_ids),
            swap_size=spec.swap_size,
            root_password=spec.root_password,
            state="running",
            dir_path=os.path.join(project_root, spec.name),
        )
        db.add(model)
        db.commit()
        return ContainerOut(
            name=model.name,
            image=model.image,
            memory_size=model.memory_size,
            gpu_ids=spec.gpu_ids,
            swap_size=model.swap_size,
            root_password=model.root_password,
            state=model.state,
        )
    finally:
        db.close()

@app.patch("/containers/{name}", response_model=ContainerOut)
def update_container(name: str, update: ContainerUpdate):
    db = SessionLocal()
    try:
        model = db.query(ContainerModel).filter_by(name=name).first()
        if not model:
            raise HTTPException(status_code=404, detail="container not found")
        key = update.key
        value = update.value
        # map key names to script arguments
        valid = {"memory_size": "update_memory", "swap_size": "update_memory", "root_password": "update_password", "gpu_ids": "update_gpu", "root_password": "update_password"}
        # For editing gpu_ids, we will call update_container.sh as required by README
        project_root = BASE_DIR
        if key in ["memory_size", "swap_size", "root_password", "gpu_ids"]:
            # call update_container script: update_container <container_name> <key> <value>
            script = os.path.join(SCRIPTS_DIR, "update_container.sh")
            # gpu_ids may be JSON list
            subprocess.run(["/bin/bash", script, name, key, value], cwd=project_root, check=False)
            # update DB
            if key == "gpu_ids":
                model.gpu_ids = value
            elif key == "memory_size":
                model.memory_size = value
            elif key == "swap_size":
                model.swap_size = value
            elif key == "root_password":
                model.root_password = value
            db.add(model)
            db.commit()
            gpu_ids = json.loads(model.gpu_ids) if model.gpu_ids else []
            return ContainerOut(name=model.name, image=model.image, memory_size=model.memory_size, gpu_ids=gpu_ids, swap_size=model.swap_size, root_password=model.root_password, state=model.state)
        else:
            raise HTTPException(status_code=400, detail="unsupported key")
    finally:
        db.close()

@app.post("/containers/{name}/action")
def container_action(name: str, action: str):
    """action in query param or body: up, down, start, stop, restart, delete"""
    db = SessionLocal()
    try:
        model = db.query(ContainerModel).filter_by(name=name).first()
        if not model:
            raise HTTPException(status_code=404, detail="container not found")
        project_root = BASE_DIR
        cmd_map = {
            "up": "container_up",
            "down": "container_down",
            "start": "container_start",
            "stop": "container_stop",
            "restart": "container_restart",
        }
        if action == "delete":
            # remove dir and db record
            if model.dir_path and os.path.isdir(model.dir_path):
                subprocess.run(["/bin/bash", "-c", f"rm -rf {model.dir_path}"], cwd=project_root, check=False)
            db.delete(model)
            db.commit()
            return {"status": "deleted"}
        elif action in cmd_map:
            cmd = ["/bin/bash", os.path.join(SCRIPTS_DIR, "container-management.sh"), "--dir", name, "--command", cmd_map[action]]
            subprocess.run(cmd, cwd=project_root, check=False)
            # update state
            if action in ["up", "start", "restart"]:
                model.state = "running"
            elif action in ["down", "stop"]:
                model.state = "stopped"
            db.add(model)
            db.commit()
            return {"status": "ok", "state": model.state}
        else:
            raise HTTPException(status_code=400, detail="unsupported action")
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

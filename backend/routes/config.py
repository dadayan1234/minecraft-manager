
from fastapi import APIRouter, HTTPException
import os

router = APIRouter()
CONFIG_PATH = "server/server.properties"

@router.get("/")
def read_config():
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="server.properties not found")
    with open(CONFIG_PATH, "r") as f:
        lines = f.readlines()
    props = {}
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key, val = line.strip().split("=", 1)
            props[key] = val
    return props

@router.post("/")
def update_config(data: dict):
    with open(CONFIG_PATH, "w") as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")
    return {"status": "updated"}

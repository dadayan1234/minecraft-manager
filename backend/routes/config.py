from fastapi import APIRouter, Depends, HTTPException
import os
from backend import auth, models
from .server import get_user_server_path # Impor dependency path

router = APIRouter()

@router.get("/config/{server_id}", summary="Membaca konfigurasi server spesifik")
def read_server_config(server_path: str = Depends(get_user_server_path)):
    config_path = os.path.join(server_path, "server.properties")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="server.properties tidak ditemukan.")
    
    props = {}
    with open(config_path, "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.strip().split("=", 1)
                props[key] = val
    return props

@router.post("/config/{server_id}", summary="Memperbarui konfigurasi server spesifik")
def update_server_config(
    data: dict,
    server_path: str = Depends(get_user_server_path)
):
    config_path = os.path.join(server_path, "server.properties")
    with open(config_path, "w") as f:
        for key, value in data.items():
            f.write(f"{key}={value}\n")
    return {"status": "updated"}
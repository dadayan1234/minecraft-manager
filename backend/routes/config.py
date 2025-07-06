from fastapi import APIRouter, Depends, HTTPException
import os
from backend import models
from backend.dependencies import get_server_details # <-- Impor dari file dependencies

router = APIRouter()

def get_server_path(server_details: dict = Depends(get_server_details)) -> str:
    """Dependency untuk mendapatkan path dari detail server yang sudah divalidasi."""
    return server_details['path']

@router.get("/config/{server_id}", summary="Membaca konfigurasi server spesifik")
def read_server_config(server_path: str = Depends(get_server_path)):
    config_path = os.path.join(server_path, "server.properties")
    if not os.path.exists(config_path):
        # Jika tidak ada, buat file kosong agar tidak error
        return {} 
    
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
    server_path: str = Depends(get_server_path)
):
    config_path = os.path.join(server_path, "server.properties")
    try:
        with open(config_path, "w") as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan konfigurasi: {e}")
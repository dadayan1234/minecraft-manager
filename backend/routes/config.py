from fastapi import APIRouter, Depends, HTTPException
import os
from backend import auth, models
# Impor helper untuk mendapatkan path server pengguna
from .server import get_user_server_path

router = APIRouter()

@router.get("/", summary="Membaca file server.properties milik pengguna")
def read_user_config(server_path: str = Depends(get_user_server_path)):
    """
    Membaca konfigurasi dari file server.properties di dalam direktori server pengguna.
    """
    config_path = os.path.join(server_path, "server.properties")
    
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="File server.properties tidak ditemukan.")
    
    props = {}
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    props[key] = val
        return props
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membaca file konfigurasi: {e}")


@router.post("/", summary="Memperbarui file server.properties milik pengguna")
def update_user_config(
    data: dict,
    server_path: str = Depends(get_user_server_path)
):
    """
    Menulis data konfigurasi baru ke file server.properties di direktori server pengguna.
    """
    config_path = os.path.join(server_path, "server.properties")
    
    try:
        with open(config_path, "w", encoding='utf-8') as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file konfigurasi: {e}")
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import os
import shutil
from backend import models
from backend.dependencies import get_server_details # <-- Impor dari file dependencies

router = APIRouter()

def get_server_path(server_details: dict = Depends(get_server_details)) -> str:
    """Dependency untuk mendapatkan path dari detail server yang sudah divalidasi."""
    return server_details['path']

@router.post("/upload/{server_id}/plugin", summary="Mengunggah plugin ke server spesifik")
def upload_plugin_to_server(
    server_path: str = Depends(get_server_path),
    uploaded_file: UploadFile = File(...)
):
    """
    Mengunggah file .jar ke dalam folder 'plugins' di direktori server yang dipilih.
    """
    if not uploaded_file.filename.endswith(".jar"):
        raise HTTPException(status_code=400, detail="Hanya file dengan ekstensi .jar yang diizinkan.")

    plugin_dir = os.path.join(server_path, "plugins")
    os.makedirs(plugin_dir, exist_ok=True)

    file_path = os.path.join(plugin_dir, uploaded_file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
        return {"status": "uploaded", "file": uploaded_file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah plugin: {e}")
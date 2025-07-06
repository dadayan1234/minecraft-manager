from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import os
import shutil
from backend import auth, models
# Impor helper untuk mendapatkan path server pengguna
from .server import get_user_server_path

router = APIRouter()

@router.post("/", summary="Mengunggah file plugin ke direktori server pengguna")
def upload_plugin_for_user(
    uploaded_file: UploadFile = File(...),
    server_path: str = Depends(get_user_server_path)
):
    """
    Mengunggah file .jar ke dalam folder 'plugins' di direktori server milik pengguna.
    """
    # Pastikan file adalah .jar
    if not uploaded_file.filename or not uploaded_file.filename.endswith(".jar"):
        raise HTTPException(status_code=400, detail="Hanya file dengan ekstensi .jar yang diizinkan.")

    # Tentukan path folder plugins spesifik pengguna
    plugin_dir = os.path.join(server_path, "plugins")
    os.makedirs(plugin_dir, exist_ok=True) # Buat folder jika belum ada

    file_path = os.path.join(plugin_dir, str(uploaded_file.filename))
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
        return {"status": "uploaded", "file": uploaded_file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah plugin: {e}")
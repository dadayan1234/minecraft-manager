
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
import os, shutil

router = APIRouter()
BASE_DIR = "server"

@router.get("/list")
def list_files(path: str = ""):
    full_path = os.path.join(BASE_DIR, path)
    if not os.path.exists(full_path):
        return {"error": "Path not found"}
    return {"files": os.listdir(full_path)}

@router.post("/upload")
def upload_file(uploaded_file: UploadFile = File(...)):
    file_path = os.path.join(BASE_DIR, uploaded_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return {"status": "uploaded"}

@router.get("/download")
def download_file(filename: str):
    path = os.path.join(BASE_DIR, filename)
    return FileResponse(path)

@router.delete("/delete")
def delete_file(filename: str):
    path = os.path.join(BASE_DIR, filename)
    os.remove(path)
    return {"status": "deleted"}

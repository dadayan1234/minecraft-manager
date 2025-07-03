
from fastapi import APIRouter, UploadFile, File
import os, shutil

router = APIRouter()
PLUGIN_DIR = "server/plugins"

@router.post("/")
def upload_plugin(uploaded_file: UploadFile = File(...)):
    if not uploaded_file.filename.endswith(".jar"):
        return {"error": "Only .jar files allowed"}
    os.makedirs(PLUGIN_DIR, exist_ok=True)
    file_path = os.path.join(PLUGIN_DIR, uploaded_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return {"status": "uploaded", "file": uploaded_file.filename}

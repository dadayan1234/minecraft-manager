import os
import shutil
import asyncio
import json
import io
import zipfile
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter()
BASE_DIR = "server"


def secure_path(path):
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not abs_path.startswith(os.path.abspath(BASE_DIR)):
        raise PermissionError("Forbidden path")
    return abs_path


@router.get("/files")
def list_files(path: str = ""):
    abs_path = secure_path(path)
    if not os.path.exists(abs_path):
        return JSONResponse(status_code=404, content={"error": "Path not found"})
    items = []
    for item in os.listdir(abs_path):
        full = os.path.join(abs_path, item)
        items.append({
            "name": item,
            "type": "folder" if os.path.isdir(full) else "file"
        })
    return {"files": items}


@router.post("/files/delete")
def delete_item(path: str = Form(...)):
    abs_path = secure_path(path)
    if not os.path.exists(abs_path):
        return {"error": "Path not found"}
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
    else:
        os.remove(abs_path)
    return {"status": "deleted"}


@router.post("/files/mkdir")
def make_directory(path: str = Form(...)):
    abs_path = secure_path(path)
    os.makedirs(abs_path, exist_ok=True)
    return {"status": "created"}


@router.post("/files/upload")
async def upload_file(path: str = Form(...), file: UploadFile = File(...)):
    abs_path = secure_path(path)
    os.makedirs(abs_path, exist_ok=True)
    file_path = os.path.join(abs_path, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"status": "uploaded", "filename": file.filename}


@router.post("/files/rename")
def rename_file(old_path: str = Form(...), new_path: str = Form(...)):
    abs_old = secure_path(old_path)
    abs_new = secure_path(new_path)
    os.rename(abs_old, abs_new)
    return {"status": "renamed"}


@router.get("/files/zip")
def download_zip(path: str = ""):
    abs_path = secure_path(path)
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode="w") as zf:
        for root, dirs, files in os.walk(abs_path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, BASE_DIR)
                zf.write(full, rel)
    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=download.zip"})


@router.post("/files/backup")
def backup_selected(request: Request):
    zip_io = io.BytesIO()
    items = asyncio.run(request.body())
    items = json.loads(items)["items"]

    with zipfile.ZipFile(zip_io, mode="w") as zf:
        for path in items:
            abs_path = secure_path(path)
            if os.path.isdir(abs_path):
                for root, dirs, files in os.walk(abs_path):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, BASE_DIR)
                        zf.write(full_path, rel_path)
            elif os.path.isfile(abs_path):
                zf.write(abs_path, path)
    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=backup.zip"})

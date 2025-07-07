import os
import shutil
import mimetypes
import zipfile
import io
from datetime import datetime
from fastapi import (
    APIRouter, Depends, UploadFile, File, Form, HTTPException, 
    Path, Query, Body, Response
)
from fastapi.responses import StreamingResponse
from typing import List
from backend.dependencies import get_server_details

router = APIRouter()

# --- DEPENDENCY HELPER ---
def get_server_path(server_details: dict = Depends(get_server_details)) -> str:
    """Dependency untuk mendapatkan path dari detail server yang sudah divalidasi."""
    return server_details['path']

# --- FUNGSI UTILITAS ---
def format_file_size(size_bytes):
    if size_bytes == 0: return "0 B"
    names = ("B", "KB", "MB", "GB")
    i = 0
    while size_bytes >= 1024 and i < len(names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{round(size_bytes, 1)} {names[i]}"

def get_file_icon(filename, is_dir=False):
    if is_dir: return "📁"
    ext = os.path.splitext(filename)[1].lower()
    icon_map = {'.jar': '☕', '.zip': '📦', '.txt': '📄', '.log': '📜', '.json': '⚙️'}
    return icon_map.get(ext, '📄')

def secure_path(base_dir: str, relative_path: str):
    if not relative_path: relative_path = ""
    full_path = os.path.normpath(os.path.join(base_dir, relative_path))
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=403, detail="Akses ke path terlarang")
    return full_path

# --- ENDPOINT API ---

@router.get("/files/{server_id}", summary="Melihat daftar file di server spesifik")
def list_files_in_server(
    server_path: str = Depends(get_server_path),
    path: str = Query("", description="Path relatif di dalam server")
):
    abs_path = secure_path(server_path, path)
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="Path tidak ditemukan atau bukan direktori.")
    
    items = []
    for item_name in sorted(os.listdir(abs_path)):
        try:
            item_path = os.path.join(abs_path, item_name)
            is_dir = os.path.isdir(item_path)
            stat = os.stat(item_path)
            items.append({
                "name": item_name, "type": "folder" if is_dir else "file",
                "path": os.path.join(path, item_name).replace("\\", "/"),
                "icon": get_file_icon(item_name, is_dir), "size": stat.st_size,
                "size_formatted": format_file_size(stat.st_size) if not is_dir else "",
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        except OSError:
            continue
    folders = [i for i in items if i['type'] == 'folder']
    files = [i for i in items if i['type'] == 'file']
    return {"current_path": path, "files": folders + files}

@router.get("/files/{server_id}/preview", summary="Melihat pratinjau file teks")
def preview_file(
    server_path: str = Depends(get_server_path),
    path: str = Query(..., description="Path lengkap ke file")
):
    abs_path = secure_path(server_path, path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    # --- PERBAIKAN UTAMA DI SINI ---
    # Daftar ekstensi yang kita anggap aman untuk dibaca sebagai teks.
    known_text_extensions = ['.txt', '.log', '.json', '.yml', '.yaml', '.properties', '.md', '.cfg', '.conf', '.sh', '.bat']
    
    is_text_file = False
    file_ext = os.path.splitext(abs_path)[1].lower()

    # 1. Cek berdasarkan ekstensi yang kita tahu
    if file_ext in known_text_extensions:
        is_text_file = True
    
    # 2. Jika tidak ada di daftar, coba tebak menggunakan mimetypes
    if not is_text_file:
        mime_type, _ = mimetypes.guess_type(abs_path)
        if mime_type and mime_type.startswith('text/'):
            is_text_file = True

    if not is_text_file:
        raise HTTPException(status_code=400, detail="Pratinjau hanya untuk file berbasis teks.")
    
    if os.path.getsize(abs_path) > 2 * 1024 * 1024: # Batas 2MB
        raise HTTPException(status_code=400, detail="File terlalu besar untuk pratinjau.")

    with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return {"content": content}

@router.get("/files/{server_id}/download", summary="Mengunduh satu file")
def download_single_file(
    server_path: str = Depends(get_server_path),
    path: str = Query(..., description="Path ke file yang akan diunduh")
):
    abs_path = secure_path(server_path, path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")
    
    with open(abs_path, "rb") as f:
        content = f.read()
        
    return Response(content=content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={os.path.basename(abs_path)}"})

@router.post("/files/{server_id}/upload", summary="Mengunggah satu atau lebih file")
async def upload_files(
    server_path: str = Depends(get_server_path),
    files: List[UploadFile] = File(...),
    path: str = Form("")
):
    upload_dir = secure_path(server_path, path)
    if not os.path.isdir(upload_dir):
        raise HTTPException(status_code=400, detail="Path tujuan bukan direktori.")
    
    for file in files:
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
    return {"info": f"{len(files)} file berhasil diunggah."}

@router.post("/files/{server_id}/rename", summary="Mengganti nama file atau folder")
def rename_item(
    server_path: str = Depends(get_server_path),
    old_path: str = Form(...),
    new_name: str = Form(...)
):
    abs_old_path = secure_path(server_path, old_path)
    if not os.path.exists(abs_old_path):
        raise HTTPException(status_code=404, detail="Item yang akan diganti nama tidak ditemukan.")
    
    parent_dir = os.path.dirname(abs_old_path)
    abs_new_path = os.path.join(parent_dir, new_name)
    
    if os.path.exists(abs_new_path):
        raise HTTPException(status_code=400, detail="Nama baru sudah ada di direktori ini.")
        
    os.rename(abs_old_path, abs_new_path)
    return {"status": "renamed", "new_name": new_name}

@router.post("/files/{server_id}/delete", summary="Menghapus file atau folder")
def delete_item(
    server_path: str = Depends(get_server_path),
    path: str = Form(...)
):
    abs_path = secure_path(server_path, path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Item tidak ditemukan.")
    if abs_path == os.path.abspath(server_path):
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus direktori root server.")
    
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
    else:
        os.remove(abs_path)
    return {"status": "deleted", "path": path}

@router.post("/files/{server_id}/copy", summary="Menyalin file atau folder")
def copy_item(
    server_path: str = Depends(get_server_path),
    source_path: str = Form(...),
    destination_path: str = Form(...)
):
    abs_source = secure_path(server_path, source_path)
    abs_dest_dir = secure_path(server_path, destination_path)
    if not os.path.exists(abs_source):
        raise HTTPException(status_code=404, detail="Sumber tidak ditemukan")
    if not os.path.isdir(abs_dest_dir):
        raise HTTPException(status_code=400, detail="Tujuan harus berupa direktori")

    destination_name = os.path.basename(abs_source)
    abs_dest_final = os.path.join(abs_dest_dir, destination_name)
    if os.path.exists(abs_dest_final):
        raise HTTPException(status_code=400, detail="File/folder dengan nama yang sama sudah ada di tujuan")

    if os.path.isdir(abs_source):
        shutil.copytree(abs_source, abs_dest_final)
    else:
        shutil.copy2(abs_source, abs_dest_final)
    return {"status": "copied"}

@router.post("/files/{server_id}/move", summary="Memindahkan file atau folder")
def move_item(
    server_path: str = Depends(get_server_path),
    source_path: str = Form(...),
    destination_path: str = Form(...)
):
    abs_source = secure_path(server_path, source_path)
    abs_dest_dir = secure_path(server_path, destination_path)
    if not os.path.exists(abs_source):
        raise HTTPException(status_code=404, detail="Sumber tidak ditemukan")
    if not os.path.isdir(abs_dest_dir):
        raise HTTPException(status_code=400, detail="Tujuan harus berupa direktori")

    destination_name = os.path.basename(abs_source)
    abs_dest_final = os.path.join(abs_dest_dir, destination_name)
    if os.path.exists(abs_dest_final):
        raise HTTPException(status_code=400, detail="File/folder dengan nama yang sama sudah ada di tujuan")
    
    shutil.move(abs_source, abs_dest_final)
    return {"status": "moved"}

@router.post("/files/{server_id}/search", summary="Mencari file di direktori server")
def search_files(
    server_path: str = Depends(get_server_path),
    query: str = Form(...),
    path: str = Form("")
):
    search_dir = secure_path(server_path, path)
    results = []
    for root, _, files in os.walk(search_dir):
        for file_name in files:
            if query.lower() in file_name.lower():
                full_path = os.path.join(root, file_name)
                results.append({
                    "name": file_name,
                    "path": os.path.relpath(full_path, server_path).replace("\\", "/"),
                })
    return {"results": results}

@router.post("/files/{server_id}/zip-selection", summary="Membuat ZIP dari file-file yang dipilih")
def download_selected_as_zip(
    server_path: str = Depends(get_server_path),
    files: List[str] = Body(..., embed=True)
):
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative_path in files:
            abs_path = secure_path(server_path, relative_path)
            if os.path.exists(abs_path):
                zf.write(abs_path, relative_path)
    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=selection.zip"})
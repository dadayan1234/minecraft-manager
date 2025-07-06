import os
import shutil
import mimetypes
import zipfile
import io
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from backend import auth, models  # Pastikan file auth.py dan models.py sudah ada

router = APIRouter()

# --- FUNGSI HELPER ---

def get_user_base_dir(current_user: models.User = Depends(auth.get_current_user)):
    """
    Mendapatkan dan membuat direktori basis untuk pengguna yang sedang login.
    Ini adalah direktori root file manager untuk setiap pengguna.
    Contoh: 'server/user_files/nama_pengguna'
    """
    # Menggunakan path dari database jika tersedia, jika tidak, buat path default
    user_dir = current_user.server_path or os.path.join("server", "user_files", current_user.username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def secure_path(base_dir: str, relative_path: str):
    """
    Memvalidasi dan mengamankan path agar tetap berada di dalam direktori basis pengguna.
    Sangat penting untuk mencegah akses ke file di luar direktori yang diizinkan (Path Traversal).
    """
    if not relative_path:
        relative_path = ""
    
    # Menormalkan path untuk konsistensi antar sistem operasi
    full_path = os.path.normpath(os.path.join(base_dir, relative_path))
    
    # Memastikan path yang dihasilkan benar-benar berada di dalam base_dir
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=403, detail="Akses ke path terlarang")
        
    return full_path

def format_file_size(size_bytes):
    """Format ukuran file agar mudah dibaca (B, KB, MB, GB)."""
    if size_bytes == 0: return "0 B"
    names = ("B", "KB", "MB", "GB")
    i = 0
    while size_bytes >= 1024 and i < len(names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{round(size_bytes, 1)} {names[i]}"

def get_file_icon(filename, is_dir=False):
    """Memberikan ikon emoji berdasarkan tipe file."""
    if is_dir: return "📁"
    ext = os.path.splitext(filename)[1].lower()
    icon_map = {
        '.jar': '☕', '.zip': '📦', '.rar': '📦', '.txt': '📄', '.log': '📜', '.json': '⚙️', 
        '.yml': '⚙️', '.properties': '⚙️', '.png': '🖼️', '.jpg': '🖼️', '.md': '📝', '.sh': '🖥️'
    }
    return icon_map.get(ext, '📄')


# --- ENDPOINT API ---

@router.get("/files", summary="Melihat daftar file dan folder pengguna")
def list_files_for_user(path: str = "", base_dir: str = Depends(get_user_base_dir)):
    abs_path = secure_path(base_dir, path)
    if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="Path tidak ditemukan")
    
    items = []
    for item_name in sorted(os.listdir(abs_path)):
        item_path = os.path.join(abs_path, item_name)
        is_dir = os.path.isdir(item_path)
        stat = os.stat(item_path)
        items.append({
            "name": item_name,
            "type": "folder" if is_dir else "file",
            "path": os.path.join(path, item_name).replace("\\", "/"),
            "icon": get_file_icon(item_name, is_dir),
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size) if not is_dir else "",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
        
    folders = [item for item in items if item["type"] == "folder"]
    files = [item for item in items if item["type"] == "file"]
    
    return {"current_path": path, "files": folders + files}

@router.post("/files/upload", summary="Mengunggah file ke direktori pengguna")
async def upload_file_for_user(
    path: str = Form(""), file: UploadFile = File(...), base_dir: str = Depends(get_user_base_dir)
):
    upload_dir = secure_path(base_dir, path)
    if not os.path.isdir(upload_dir):
         raise HTTPException(status_code=400, detail="Path tujuan harus berupa direktori")

    if not isinstance(file.filename, str) or not file.filename:
        raise HTTPException(status_code=400, detail="Nama file tidak valid")
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "uploaded", "filename": file.filename, "path": path}

@router.post("/files/mkdir", summary="Membuat folder baru")
def create_directory_for_user(
    path: str = Form(...), name: str = Form(...), base_dir: str = Depends(get_user_base_dir)
):
    parent_path = secure_path(base_dir, path)
    new_dir_path = os.path.join(parent_path, name)
    
    if os.path.exists(new_dir_path):
        raise HTTPException(status_code=400, detail="Direktori sudah ada")
    
    os.makedirs(new_dir_path)
    return {"status": "created", "path": os.path.join(path, name)}

@router.post("/files/delete", summary="Menghapus file atau folder")
def delete_item_for_user(path: str = Form(...), base_dir: str = Depends(get_user_base_dir)):
    abs_path = secure_path(base_dir, path)
    if not os.path.exists(abs_path) or abs_path == os.path.abspath(base_dir):
        raise HTTPException(status_code=404, detail="Item tidak ditemukan atau Anda tidak bisa menghapus root")
    
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
    else:
        os.remove(abs_path)
        
    return {"status": "deleted", "path": path}

@router.post("/files/rename", summary="Mengganti nama file atau folder")
def rename_item_for_user(
    old_path: str = Form(...), new_name: str = Form(...), base_dir: str = Depends(get_user_base_dir)
):
    abs_old_path = secure_path(base_dir, old_path)
    if not os.path.exists(abs_old_path):
        raise HTTPException(status_code=404, detail="Path lama tidak ditemukan")
        
    parent_dir = os.path.dirname(abs_old_path)
    abs_new_path = os.path.join(parent_dir, new_name)
    
    if os.path.exists(abs_new_path):
        raise HTTPException(status_code=400, detail="Nama baru sudah ada di lokasi ini")

    os.rename(abs_old_path, abs_new_path)
    new_relative_path = os.path.relpath(abs_new_path, base_dir).replace("\\", "/")
    return {"status": "renamed", "new_path": new_relative_path}

@router.post("/files/copy", summary="Menyalin file atau folder")
def copy_item_for_user(
    source_path: str = Form(...), destination_path: str = Form(...), base_dir: str = Depends(get_user_base_dir)
):
    abs_source = secure_path(base_dir, source_path)
    abs_dest_dir = secure_path(base_dir, destination_path)
    
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
        
    return {"status": "copied", "source": source_path, "destination": os.path.join(destination_path, destination_name)}

@router.post("/files/move", summary="Memindahkan file atau folder")
def move_item_for_user(
    source_path: str = Form(...), destination_path: str = Form(...), base_dir: str = Depends(get_user_base_dir)
):
    abs_source = secure_path(base_dir, source_path)
    abs_dest_dir = secure_path(base_dir, destination_path)

    if not os.path.exists(abs_source):
        raise HTTPException(status_code=404, detail="Sumber tidak ditemukan")
    if not os.path.isdir(abs_dest_dir):
        raise HTTPException(status_code=400, detail="Tujuan harus berupa direktori")

    destination_name = os.path.basename(abs_source)
    abs_dest_final = os.path.join(abs_dest_dir, destination_name)

    if os.path.exists(abs_dest_final):
        raise HTTPException(status_code=400, detail="File/folder dengan nama yang sama sudah ada di tujuan")
    
    shutil.move(abs_source, abs_dest_final)
    
    return {"status": "moved", "source": source_path, "destination": os.path.join(destination_path, destination_name)}

@router.post("/files/search", summary="Mencari file di direktori pengguna")
def search_files_for_user(
    query: str = Form(...), path: str = Form(""), base_dir: str = Depends(get_user_base_dir)
):
    search_dir = secure_path(base_dir, path)
    results = []
    
    for root, _, files in os.walk(search_dir):
        for file_name in files:
            if query.lower() in file_name.lower():
                file_path = os.path.join(root, file_name)
                results.append({
                    "name": file_name,
                    "path": os.path.relpath(file_path, base_dir).replace("\\", "/"),
                })
    return {"results": results, "query": query}

@router.get("/files/download", summary="Mengunduh file")
def download_file_for_user(path: str, base_dir: str = Depends(get_user_base_dir)):
    abs_path = secure_path(base_dir, path)
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan atau merupakan direktori")
    
    return FileResponse(abs_path, filename=os.path.basename(abs_path))

@router.get("/files/preview", summary="Melihat pratinjau konten file teks")
def preview_file_for_user(path: str, base_dir: str = Depends(get_user_base_dir)):
    abs_path = secure_path(base_dir, path)
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    mime_type, _ = mimetypes.guess_type(abs_path)
    if not mime_type or not mime_type.startswith('text/'):
        raise HTTPException(status_code=400, detail="Pratinjau hanya untuk file berbasis teks")

    if os.path.getsize(abs_path) > 1 * 1024 * 1024: # Batas 1MB
         raise HTTPException(status_code=400, detail="File terlalu besar untuk pratinjau")

    with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    return {"content": content, "path": path}

@router.get("/files/zip", summary="Mengunduh direktori sebagai file ZIP")
def download_zip_for_user(path: str = "", base_dir: str = Depends(get_user_base_dir)):
    abs_path = secure_path(base_dir, path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Path tidak ditemukan")

    zip_io = io.BytesIO()
    zip_name = os.path.basename(path) if path else "archive"
    
    with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(abs_path):
            for root, _, files in os.walk(abs_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, abs_path)
                    zf.write(file_path, arc_path)
        else:
             zf.write(abs_path, os.path.basename(abs_path))

    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_name}.zip"}
    )
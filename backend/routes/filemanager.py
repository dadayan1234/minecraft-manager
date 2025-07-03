import os
import shutil
import asyncio
import json
import io
import zipfile
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pathlib import Path
import mimetypes

router = APIRouter()
BASE_DIR = "server"

def secure_path(path):
    """Ensure path is within BASE_DIR for security"""
    if not path:
        path = ""
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    base_abs = os.path.abspath(BASE_DIR)
    if not abs_path.startswith(base_abs):
        raise HTTPException(status_code=403, detail="Forbidden path")
    return abs_path

def get_file_info(file_path):
    """Get detailed file information"""
    stat = os.stat(file_path)
    return {
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "is_readable": os.access(file_path, os.R_OK),
        "is_writable": os.access(file_path, os.W_OK),
    }

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def get_file_icon(filename, is_dir=False):
    """Get appropriate icon for file type"""
    if is_dir:
        return "📁"
    
    ext = os.path.splitext(filename)[1].lower()
    icon_map = {
        '.jar': '☕',
        '.zip': '📦',
        '.rar': '📦',
        '.7z': '📦',
        '.txt': '📄',
        '.log': '📜',
        '.json': '⚙️',
        '.yml': '⚙️',
        '.yaml': '⚙️',
        '.properties': '⚙️',
        '.cfg': '⚙️',
        '.conf': '⚙️',
        '.png': '🖼️',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.gif': '🖼️',
        '.webp': '🖼️',
        '.pdf': '📕',
        '.md': '📝',
        '.sh': '🖥️',
        '.bat': '🖥️',
        '.cmd': '🖥️',
    }
    return icon_map.get(ext, '📄')

@router.get("/files")
def list_files(path: str = ""):
    """List files and directories with detailed information"""
    try:
        abs_path = secure_path(path)
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        items = []
        
        # Add parent directory if not at root
        if path:
            parent_parts = path.split('/')[:-1] if '/' in path else []
            parent_path = '/'.join(parent_parts)
            items.append({
                "name": "..",
                "type": "parent",
                "path": parent_path,
                "icon": "⬆️",
                "size": 0,
                "size_formatted": "",
                "modified": "",
                "is_readable": True,
                "is_writable": True
            })
        
        # List directory contents
        for item in sorted(os.listdir(abs_path)):
            if item.startswith('.'):  # Skip hidden files
                continue
                
            full_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(full_path)
            
            try:
                file_info = get_file_info(full_path)
                item_path = f"{path}/{item}" if path else item
                
                items.append({
                    "name": item,
                    "type": "folder" if is_dir else "file",
                    "path": item_path,
                    "icon": get_file_icon(item, is_dir),
                    "size": file_info["size"],
                    "size_formatted": format_file_size(file_info["size"]) if not is_dir else "",
                    "modified": file_info["modified"],
                    "is_readable": file_info["is_readable"],
                    "is_writable": file_info["is_writable"]
                })
            except (OSError, PermissionError):
                # Skip files that can't be accessed
                continue
        
        # Separate folders and files, folders first
        folders = [item for item in items if item["type"] in ["parent", "folder"]]
        files = [item for item in items if item["type"] == "file"]
        
        return {
            "current_path": path,
            "files": folders + files,
            "total_items": len(items)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/mkdir")
def create_directory(path: str = Form(...), name: str = Form(...)):
    """Create a new directory"""
    try:
        parent_path = secure_path(path)
        new_dir_path = os.path.join(parent_path, name)
        
        if os.path.exists(new_dir_path):
            raise HTTPException(status_code=400, detail="Directory already exists")
        
        os.makedirs(new_dir_path, exist_ok=False)
        return {"status": "created", "path": f"{path}/{name}" if path else name}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/upload")
async def upload_file(path: str = Form(...), file: UploadFile = File(...)):
    """Upload a file to specified path"""
    try:
        abs_path = secure_path(path)
        
        if not os.path.exists(abs_path):
            os.makedirs(abs_path, exist_ok=True)
        
        file_path = os.path.join(abs_path, file.filename)
        
        # Check if file already exists
        if os.path.exists(file_path):
            # Create backup name with timestamp
            name, ext = os.path.splitext(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(abs_path, f"{name}_{timestamp}{ext}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "status": "uploaded", 
            "filename": file.filename,
            "size": len(content),
            "size_formatted": format_file_size(len(content))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/delete")
def delete_item(path: str = Form(...)):
    """Delete a file or directory"""
    try:
        abs_path = secure_path(path)
        
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        
        return {"status": "deleted", "path": path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/rename")
def rename_item(old_path: str = Form(...), new_name: str = Form(...)):
    """Rename a file or directory"""
    try:
        abs_old_path = secure_path(old_path)
        
        if not os.path.exists(abs_old_path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        # Get parent directory and create new path
        parent_dir = os.path.dirname(abs_old_path)
        new_path = os.path.join(parent_dir, new_name)
        
        if os.path.exists(new_path):
            raise HTTPException(status_code=400, detail="Name already exists")
        
        os.rename(abs_old_path, new_path)
        
        # Calculate new relative path
        new_relative = os.path.relpath(new_path, secure_path(""))
        
        return {"status": "renamed", "new_path": new_relative}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/copy")
def copy_item(source_path: str = Form(...), dest_path: str = Form(...)):
    """Copy a file or directory"""
    try:
        abs_source = secure_path(source_path)
        abs_dest = secure_path(dest_path)
        
        if not os.path.exists(abs_source):
            raise HTTPException(status_code=404, detail="Source path not found")
        
        if os.path.exists(abs_dest):
            raise HTTPException(status_code=400, detail="Destination already exists")
        
        if os.path.isdir(abs_source):
            shutil.copytree(abs_source, abs_dest)
        else:
            shutil.copy2(abs_source, abs_dest)
        
        return {"status": "copied", "source": source_path, "destination": dest_path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/move")
def move_item(source_path: str = Form(...), dest_path: str = Form(...)):
    """Move a file or directory"""
    try:
        abs_source = secure_path(source_path)
        abs_dest = secure_path(dest_path)
        
        if not os.path.exists(abs_source):
            raise HTTPException(status_code=404, detail="Source path not found")
        
        if os.path.exists(abs_dest):
            raise HTTPException(status_code=400, detail="Destination already exists")
        
        shutil.move(abs_source, abs_dest)
        
        return {"status": "moved", "source": source_path, "destination": dest_path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/download")
def download_file(path: str):
    """Download a file"""
    try:
        abs_path = secure_path(path)
        
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        filename = os.path.basename(abs_path)
        return FileResponse(
            abs_path, 
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/preview")
def preview_file(path: str):
    """Preview file content (for text files)"""
    try:
        abs_path = secure_path(path)
        
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file is text-based
        mime_type, _ = mimetypes.guess_type(abs_path)
        if mime_type and not mime_type.startswith('text/'):
            return {"error": "File is not previewable", "type": mime_type}
        
        # Limit preview size to 1MB
        if os.path.getsize(abs_path) > 1024 * 1024:
            return {"error": "File too large for preview"}
        
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return {
            "content": content,
            "size": len(content),
            "type": mime_type or "text/plain"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/zip")
def download_zip(path: str = ""):
    """Download directory as ZIP file"""
    try:
        abs_path = secure_path(path)
        
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        zip_io = io.BytesIO()
        zip_name = os.path.basename(path) if path else "minecraft_server"
        
        with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(abs_path):
                for root, dirs, files in os.walk(abs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, abs_path)
                        zf.write(file_path, arc_path)
            else:
                zf.write(abs_path, os.path.basename(abs_path))
        
        zip_io.seek(0)
        return StreamingResponse(
            io.BytesIO(zip_io.read()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_name}.zip"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/search")
def search_files(query: str = Form(...), path: str = Form("")):
    """Search files by name"""
    try:
        abs_path = secure_path(path)
        results = []
        
        for root, dirs, files in os.walk(abs_path):
            for file in files:
                if query.lower() in file.lower():
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, secure_path(""))
                    try:
                        file_info = get_file_info(file_path)
                        results.append({
                            "name": file,
                            "path": rel_path,
                            "directory": os.path.relpath(root, secure_path("")),
                            "size": file_info["size"],
                            "size_formatted": format_file_size(file_info["size"]),
                            "modified": file_info["modified"],
                            "icon": get_file_icon(file)
                        })
                    except (OSError, PermissionError):
                        continue
        
        return {"results": results, "query": query, "total": len(results)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
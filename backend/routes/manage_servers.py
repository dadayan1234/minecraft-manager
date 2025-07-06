import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import os
import shutil
from backend import auth, models
from backend.database import create_connection

router = APIRouter()

class ServerCreate(BaseModel):
    name: str
    version: str

class ServerInfo(BaseModel):
    id: int
    name: str
    version: str

@router.post("/servers", response_model=ServerInfo, summary="Membuat instance server baru")
def create_server(
    server_data: ServerCreate,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Membuat direktori dan mencatat server baru ke database untuk pengguna."""
    server_name = server_data.name
    server_path = os.path.join("server", "user_files", current_user.username, server_name)
    
    if os.path.exists(server_path):
        raise HTTPException(status_code=400, detail="Server dengan nama ini sudah ada.")
    
    os.makedirs(server_path, exist_ok=True)
    
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Gagal terhubung ke database.")
    cursor = conn.cursor()
    try:
        # Dapatkan user_id dari username
        cursor.execute("SELECT id FROM users WHERE username = ?", (current_user.username,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
        user_id = user_row['id']
        
        cursor.execute(
            "INSERT INTO servers (user_id, name, version, path) VALUES (?, ?, ?, ?)",
            (user_id, server_name, server_data.version, server_path)
        )
        new_server_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Path server sudah terdaftar.")
    finally:
        conn.close()
    
    if new_server_id is None:
        raise HTTPException(status_code=500, detail="Gagal mendapatkan ID server baru.")
        
    return ServerInfo(id=new_server_id, name=server_name, version=server_data.version)

@router.get("/servers", response_model=List[ServerInfo], summary="Melihat semua server milik pengguna")
def list_servers(current_user: models.User = Depends(auth.get_current_user)):
    """Mengambil daftar semua server yang telah dibuat oleh pengguna."""
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Gagal terhubung ke database.")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.name, s.version FROM servers s
        JOIN users u ON s.user_id = u.id
        WHERE u.username = ?
    """, (current_user.username,))
    
    servers = [ServerInfo(id=row['id'], name=row['name'], version=row['version']) for row in cursor.fetchall()]
    conn.close()
    return servers

@router.delete("/servers/{server_id}", status_code=204, summary="Menghapus server")
def delete_server(
    server_id: int,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Menghapus server dari database dan menghapus direktorinya dari sistem file."""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Verifikasi kepemilikan dan dapatkan path
    cursor.execute("""
        SELECT s.path FROM servers s JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND u.username = ?
    """, (server_id, current_user.username))
    server_row = cursor.fetchone()

    if not server_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Server tidak ditemukan atau bukan milik Anda.")
    
    server_path = server_row['path']
    
    # Hapus dari database
    cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    conn.commit()
    conn.close()
    
    # Hapus direktori dari sistem file
    if os.path.exists(server_path):
        shutil.rmtree(server_path)
        
    return
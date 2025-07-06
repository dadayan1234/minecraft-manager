from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import List
import asyncio
import os
from backend import auth, models # Impor auth dan models
from backend.dependencies import get_server_details

router = APIRouter()

# Objek untuk mengelola koneksi aktif
class ConnectionManager:
    def __init__(self):
        # Struktur: {server_id: [websocket1, websocket2]}
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.active_connections:
            self.active_connections[server_id] = []
        self.active_connections[server_id].append(websocket)

    def disconnect(self, websocket: WebSocket, server_id: int):
        if server_id in self.active_connections:
            self.active_connections[server_id].remove(websocket)

manager = ConnectionManager()

async def get_current_user_from_token(token: str = Query(...)):
    """Fungsi helper untuk memvalidasi token dari query param WebSocket."""
    # Ini adalah adaptasi dari get_current_user untuk WebSocket
    try:
        return await auth.get_current_user(token)
    except:
        return None

@router.websocket("/ws/log/{server_id}")
async def websocket_log_for_server(
    websocket: WebSocket,
    server_id: int,
    token: str = Query(...)
):
    # 1. Validasi Token dan Kepemilikan Server
    user = await auth.get_current_user(token)
    if not user:
        await websocket.close(code=1008, reason="Token tidak valid")
        return
        
    conn = auth.create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT path FROM servers s JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND u.username = ?
    """, (server_id, user.username))
    server_data = cursor.fetchone()
    conn.close()

    if not server_data:
        await websocket.close(code=1008, reason="Akses ke server tidak diizinkan")
        return

    server_path = server_data['path']
    await manager.connect(websocket, server_id)
    
    log_path = os.path.join(server_path, "logs", "latest.log")

    try:
        if not os.path.exists(log_path):
            await websocket.send_text("File log tidak ditemukan. Mulai server terlebih dahulu.")
            while not os.path.exists(log_path):
                await asyncio.sleep(2)
        
        with open(log_path, "r", encoding='utf-8', errors='ignore') as log_file:
            log_file.seek(0, os.SEEK_END)
            while True:
                line = log_file.readline()
                if line:
                    await websocket.send_text(line)
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, server_id)
    except Exception:
        manager.disconnect(websocket, server_id)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import List
import asyncio
import os
from backend import auth, models # Impor auth dan models

router = APIRouter()

# Objek untuk mengelola koneksi aktif
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        if username not in self.active_connections:
            self.active_connections[username] = []
        self.active_connections[username].append(websocket)

    def disconnect(self, websocket: WebSocket, username: str):
        if username in self.active_connections:
            self.active_connections[username].remove(websocket)

manager = ConnectionManager()

async def get_current_user_from_token(token: str = Query(...)):
    """Fungsi helper untuk memvalidasi token dari query param WebSocket."""
    # Ini adalah adaptasi dari get_current_user untuk WebSocket
    try:
        return await auth.get_current_user(token)
    except:
        return None

@router.websocket("/ws/log")
async def websocket_log_for_user(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint untuk streaming log server spesifik pengguna."""
    user = await get_current_user_from_token(token)
    if user is None:
        await websocket.close(code=1008, reason="Invalid authentication credentials")
        return

    await manager.connect(websocket, user.username)

    # Tentukan path log spesifik untuk pengguna ini
    log_path = os.path.join(user.server_path or f"server/user_files/{user.username}", "logs", "latest.log")

    try:
        if not os.path.exists(log_path):
            await websocket.send_text("File log tidak ditemukan. Mulai server terlebih dahulu.")
            # Tetap buka koneksi untuk menunggu file dibuat
            while not os.path.exists(log_path):
                await asyncio.sleep(2)
        
        with open(log_path, "r", encoding='utf-8', errors='ignore') as log_file:
            log_file.seek(0, os.SEEK_END)  # Mulai dari akhir file
            while True:
                if line := log_file.readline():
                    await websocket.send_text(line)
                await asyncio.sleep(0.5) # Cek file setiap 0.5 detik
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.username)
        print(f"Client {user.username} disconnected from log stream.")
    except Exception as e:
        print(f"Error on log stream for {user.username}: {e}")
        manager.disconnect(websocket, user.username)
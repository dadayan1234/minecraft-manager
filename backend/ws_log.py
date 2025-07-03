
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import asyncio
import os

router = APIRouter()
clients = set()

@router.websocket("/ws/log")
async def websocket_log_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        log_path = "server/logs/latest.log"
        if not os.path.exists(log_path):
            await websocket.send_text("Log file not found.")
            return
        with open(log_path, "r") as log_file:
            log_file.seek(0, os.SEEK_END)
            while True:
                line = log_file.readline()
                if line:
                    await websocket.send_text(line)
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        clients.remove(websocket)

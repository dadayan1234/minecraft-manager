# backend/routes/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

router = APIRouter()
log_clients = []

@router.websocket("/ws/log")
async def websocket_log(websocket: WebSocket):
    await websocket.accept()
    log_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # dummy
    except WebSocketDisconnect:
        log_clients.remove(websocket)

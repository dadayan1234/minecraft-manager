from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List, Dict
from backend import auth

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.active_connections:
            self.active_connections[server_id] = []
        self.active_connections[server_id].append(websocket)

    def disconnect(self, websocket: WebSocket, server_id: int):
        if server_id in self.active_connections and websocket in self.active_connections[server_id]:
            self.active_connections[server_id].remove(websocket)

    async def broadcast_to_server(self, server_id: int, message: str):
        if server_id in self.active_connections:
            for connection in self.active_connections[server_id][:]:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.disconnect(connection, server_id)

manager = ConnectionManager()

@router.websocket("/ws/log/{server_id}")
async def websocket_log_for_server(
    websocket: WebSocket,
    server_id: int,
    token: str = Query(...)
):
    user = await auth.get_current_user(token)
    if not user:
        await websocket.close(code=1008, reason="Token tidak valid")
        return
    
    await manager.connect(websocket, server_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, server_id)
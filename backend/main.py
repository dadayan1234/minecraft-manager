
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes import file, server, command, config
import os
from backend.routes.websocket import router as websocket_router
from backend.routes import tunnel
from backend.routes import filemanager



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(file.router, prefix="/file")
app.include_router(server.router, prefix="/server")
app.include_router(command.router, prefix="/cmd")
app.include_router(config.router, prefix="/config")
app.include_router(websocket_router)
app.include_router(tunnel.router)
app.include_router(filemanager.router)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")

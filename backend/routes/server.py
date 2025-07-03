
from fastapi import APIRouter
import subprocess
import asyncio
from backend.routes.websocket import log_clients
import os

router = APIRouter()
process = None

# Fungsi ini untuk streaming log secara threading (bukan async)
from threading import Thread
from backend.routes.websocket import log_clients

def stream_logs(proc):
    for line in proc.stdout:
        decoded = line.decode("utf-8")
        for client in log_clients:
            try:
                import asyncio
                asyncio.run(client.send_text(decoded))
            except:
                pass

@router.post("/start")
def start_server():
    global process

    if process is not None and process.poll() is None:
        return {"status": "already running"}

    # Pastikan direktori server ada
    os.makedirs("server", exist_ok=True)

    # Jalankan Minecraft server
    process = subprocess.Popen(
        ["java", "-Xmx1024M", "-Xms1024M", "-jar", "minecraft.jar", "nogui"],
        cwd="server",  # ⬅️ semua file akan tersimpan di folder ini
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Jalankan thread untuk log streaming
    log_thread = Thread(target=stream_logs, args=(process,))
    log_thread.start()

    return {"status": "starting"}

@router.post("/stop")
def stop_server():
    global process
    if process:
        process.terminate()
        process = None
        return {"status": "stopped"}
    return {"status": "not running"}

@router.get("/status")
def server_status():
    global process
    if process is not None and process.poll() is None:
        return {"running": True}
    return {"running": False}


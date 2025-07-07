import subprocess
import os
import time
import httpx
import threading
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from backend import models
from backend.dependencies import get_server_details
from backend.shared_state import server_processes
from backend.routes.websocket import manager

router = APIRouter()

def log_streamer(server_id: int, process: subprocess.Popen):
    """
    Fungsi ini berjalan di thread terpisah. Tugasnya hanya membaca output
    dari proses server dan menyiarkannya melalui ConnectionManager.
    """
    try:
        # Loop ini akan berjalan selama proses server menghasilkan output
        for line in iter(process.stdout.readline, ''):
            # Kirim setiap baris ke semua klien yang relevan secara async
            asyncio.run(manager.broadcast_to_server(server_id, line))
    except Exception as e:
        print(f"Error di dalam log_streamer untuk server_id {server_id}: {e}")
    finally:
        process.stdout.close()
        print(f"Log streamer untuk server_id: {server_id} telah berhenti.")

async def download_server_jar(version: str, path: str) -> str:
    jar_name = f"server-{version}.jar"
    jar_path = os.path.join(path, jar_name)
    if os.path.exists(jar_path): return jar_name
    MOJANG_VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    try:
        async with httpx.AsyncClient() as client:
            manifest_res = await client.get(MOJANG_VERSION_MANIFEST_URL)
            version_url = next((v['url'] for v in manifest_res.json()['versions'] if v['id'] == version), None)
            if not version_url: raise ValueError(f"Versi {version} tidak ditemukan.")
            version_detail_res = await client.get(version_url)
            server_download_url = version_detail_res.json().get("downloads", {}).get("server", {}).get("url")
            if not server_download_url: raise ValueError(f"URL download untuk versi {version} tidak ditemukan.")
            with open(jar_path, "wb") as f:
                async with client.stream("GET", server_download_url, timeout=300.0) as response:
                    async for chunk in response.aiter_bytes(): f.write(chunk)
            return jar_name
    except Exception as e:
        if os.path.exists(jar_path): os.remove(jar_path)
        raise HTTPException(status_code=500, detail=f"Gagal mengunduh server jar: {str(e)}")

def initialize_server_files(server_path: str, jar_name: str):
    properties_path = os.path.join(server_path, "server.properties")
    if os.path.exists(properties_path): return
    try:
        init_process = subprocess.Popen(["java", "-Xmx1024M", "-Xms1024M", "-jar", jar_name, "nogui"], cwd=server_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(7) # Beri waktu lebih untuk inisialisasi
        init_process.kill()
    except Exception as e:
        print(f"Peringatan: Gagal saat inisialisasi file server: {e}")

@router.post("/servers/{server_id}/start", summary="Memulai server spesifik")
async def start_server(server_details: dict = Depends(get_server_details)):
    server_id = server_details['id']
    server_path = server_details['path']
    server_version = server_details['version']

    if server_processes.get(server_id) and server_processes[server_id].poll() is None:
        raise HTTPException(status_code=400, detail="Server ini sudah berjalan.")

    eula_path = os.path.join(server_path, "eula.txt")
    if not os.path.exists(eula_path):
        with open(eula_path, "w") as f: f.write("eula=true\n")

    jar_to_run = await download_server_jar(server_version, server_path)
    initialize_server_files(server_path, jar_to_run)

    try:
        process = subprocess.Popen(
            ["java", "-Xmx1024M", "-Xms1024M", "-jar", jar_to_run, "nogui"],
            cwd=server_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace'
        )
        server_processes[server_id] = process

        stream_thread = threading.Thread(target=log_streamer, args=(server_id, process))
        stream_thread.daemon = True
        stream_thread.start()
        
        return {"status": "starting", "server_id": server_id}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Perintah 'java' tidak ditemukan. Pastikan Java terinstall dan ada di PATH sistem Anda.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memulai server: {str(e)}")

@router.post("/servers/{server_id}/stop", summary="Menghentikan server spesifik")
def stop_server(server_details: dict = Depends(get_server_details)):
    server_id = server_details['id']
    process = server_processes.get(server_id)
    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server ini tidak sedang berjalan.")
    try:
        process.stdin.write("stop\n")
        process.stdin.flush()
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
    finally:
        server_processes.pop(server_id, None)
    return {"status": "stopped", "server_id": server_id}

@router.get("/servers/{server_id}/status", summary="Melihat status server spesifik")
def get_server_status(server_details: dict = Depends(get_server_details)):
    server_id = server_details['id']
    process = server_processes.get(server_id)
    if process and process.poll() is None:
        return {"running": True}
    return {"running": False}

@router.post("/servers/{server_id}/command", summary="Mengirim perintah ke server spesifik")
def send_command(
    command_data: models.Command,
    server_details: dict = Depends(get_server_details)
):
    server_id = server_details['id']
    process = server_processes.get(server_id)
    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server tidak berjalan.")
    try:
        process.stdin.write(command_data.command + '\n')
        process.stdin.flush()
        return {"status": "command_sent", "command": command_data.command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengirim perintah: {str(e)}")
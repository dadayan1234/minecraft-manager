import subprocess
import os
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from backend import auth, models
from backend.database import create_connection
from backend.routes.versions import MOJANG_VERSION_MANIFEST_URL
from backend.routes.websocket import manager  # Impor ConnectionManager dari websocket.py
import httpx
import os

router = APIRouter()

# Dictionary untuk menyimpan proses server yang sedang berjalan untuk setiap pengguna
# Key: username (str), Value: process (subprocess.Popen)
user_processes = {}
server_processes = {}

async def get_server_details(
    server_id: Annotated[int, Path(title="The ID of the server to operate on.")],
    current_user: models.User = Depends(auth.get_current_user)
) -> dict:
    """
    Dependency yang memverifikasi kepemilikan server dan mengembalikan detailnya.
    Ini adalah kunci keamanan untuk memastikan pengguna tidak bisa mengontrol server orang lain.
    """
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.path, s.version FROM servers s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ? AND u.username = ?
    """, (server_id, current_user.username))
    server_data = cursor.fetchone()
    conn.close()
    
    if not server_data:
        raise HTTPException(status_code=404, detail="Server tidak ditemukan atau Anda tidak memiliki akses.")
    
    return dict(server_data)

def get_user_server_path(current_user: models.User = Depends(auth.get_current_user)):
    """
    Mendapatkan dan membuat direktori server spesifik untuk pengguna yang sedang login.
    """
    # Menggunakan path dari database atau membuat path default
    server_path = current_user.server_path or os.path.join("server", "user_files", current_user.username)
    os.makedirs(server_path, exist_ok=True)
    return server_path

async def download_server_jar(version: str, path: str) -> str:
    """
    Mengunduh file server.jar untuk versi yang spesifik jika belum ada.
    Mengembalikan nama file jar yang akan dieksekusi.
    """
    jar_name = f"server-{version}.jar"
    jar_path = os.path.join(path, jar_name)

    if os.path.exists(jar_path):
        return jar_name # Jar sudah ada, tidak perlu download

    try:
        # 1. Dapatkan manifest utama
        async with httpx.AsyncClient() as client:
            manifest_res = await client.get(MOJANG_VERSION_MANIFEST_URL)
            manifest_data = manifest_res.json()
            
            # 2. Cari URL untuk detail versi yang dipilih
            version_url = next((v['url'] for v in manifest_data['versions'] if v['id'] == version), None)
            if not version_url:
                raise HTTPException(status_code=404, detail=f"Versi {version} tidak ditemukan.")

            # 3. Dapatkan detail versi untuk menemukan URL download server
            version_detail_res = await client.get(version_url)
            version_detail_data = version_detail_res.json()
            
            server_download_url = version_detail_data.get("downloads", {}).get("server", {}).get("url")
            if not server_download_url:
                raise HTTPException(status_code=404, detail=f"URL download server untuk versi {version} tidak ditemukan.")

            # 4. Download file server.jar
            print(f"Mengunduh server.jar untuk versi {version}...")
            with open(jar_path, "wb") as f:
                async with client.stream("GET", server_download_url, timeout=300.0) as response:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            print("Unduhan selesai.")
            return jar_name

    except Exception as e:
        # Jika download gagal, hapus file yang mungkin tidak lengkap
        if os.path.exists(jar_path):
            os.remove(jar_path)
        raise HTTPException(status_code=500, detail=f"Gagal mengunduh server jar: {e}")


@router.post("/servers/{server_id}/start", summary="Memulai server spesifik milik pengguna")
async def start_server(server_details: dict = Depends(get_server_details)):
    server_id = server_details['id']
    server_path = server_details['path']
    server_version = server_details['version']

    if server_processes.get(server_id) and server_processes[server_id].poll() is None:
        raise HTTPException(status_code=400, detail="Server ini sudah berjalan.")

    eula_path = os.path.join(server_path, "eula.txt")
    if not os.path.exists(eula_path):
        with open(eula_path, "w") as f:
            f.write("eula=true\n")

    jar_to_run = await download_server_jar(server_version, server_path)

    try:
        process = subprocess.Popen(
            ["java", "-Xmx1024M", "-Xms1024M", "-jar", jar_to_run, "nogui"],
            cwd=server_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        server_processes[server_id] = process
        return {"status": "starting", "server_id": server_id, "version": server_version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memulai server: {str(e)}")

@router.post("/servers/{server_id}/stop", summary="Menghentikan server spesifik")
def stop_server(server_id: int = Depends(lambda details: details['id'], use_cache=False)):
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
def get_server_status(server_id: int = Depends(lambda details: details['id'], use_cache=False)):
    process = server_processes.get(server_id)
    if process and process.poll() is None:
        return {"running": True}
    return {"running": False}

@router.post("/servers/{server_id}/command", summary="Mengirim perintah ke server spesifik")
def send_command(
    command_data: models.Command, # Menggunakan Pydantic model
    server_id: int = Depends(lambda details: details['id'], use_cache=False)
):
    process = server_processes.get(server_id)
    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server tidak berjalan.")
        
    try:
        process.stdin.write(command_data.command + '\n')
        process.stdin.flush()
        return {"status": "command_sent", "server_id": server_id, "command": command_data.command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengirim perintah: {str(e)}")
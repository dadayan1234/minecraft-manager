import subprocess
import os
from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/start", summary="Memulai server Minecraft untuk pengguna sesuai versi")
async def start_server_for_user(
    current_user: models.User = Depends(auth.get_current_user),
    server_path: str = Depends(get_user_server_path)
):
    """
    Memulai server sesuai versi yang dipilih pengguna.
    """
    username = current_user.username
    if user_processes.get(username) and user_processes[username].poll() is None:
        raise HTTPException(status_code=400, detail="Server untuk pengguna ini sudah berjalan.")

    # Ambil versi yang dipilih pengguna dari database
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Gagal terhubung ke database.")
    cursor = conn.cursor()
    cursor.execute("SELECT server_version FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    conn.close()
    
    selected_version = user_data['server_version'] if user_data and user_data['server_version'] else None
    if not selected_version:
        raise HTTPException(status_code=400, detail="Anda belum memilih versi server. Silakan pilih versi terlebih dahulu.")
    
    # Download jar jika perlu dan dapatkan nama file-nya
    jar_to_run = await download_server_jar(selected_version, server_path)

    # Menulis eula.txt secara otomatis jika belum ada
    eula_path = os.path.join(server_path, "eula.txt")
    if not os.path.exists(eula_path):
        with open(eula_path, "w") as f:
            f.write("eula=true\n")

    try:
        # Jalankan server dengan jar yang sesuai
        process = subprocess.Popen(
            ["java", "-Xmx1024M", "-Xms1024M", "-jar", jar_to_run, "nogui"], # <-- KUNCI PERUBAHAN
            cwd=server_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        user_processes[username] = process
        return {"status": "starting", "version": selected_version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memulai server: {e}")


@router.post("/stop", summary="Menghentikan server Minecraft milik pengguna")
def stop_server_for_user(current_user: models.User = Depends(auth.get_current_user)):
    """
    Mengirimkan perintah terminasi ke proses server milik pengguna yang sedang login.
    """
    username = current_user.username
    process = user_processes.get(username)

    if process and process.poll() is None:
        try:
            process.terminate()  # Mengirim sinyal SIGTERM
            process.wait(timeout=10) # Menunggu proses benar-benar berhenti
            user_processes.pop(username, None)
            return {"status": "stopped", "detail": f"Server untuk pengguna {username} telah dihentikan."}
        except subprocess.TimeoutExpired:
             process.kill() # Jika terminate gagal, paksa kill
             user_processes.pop(username, None)
             return {"status": "killed", "detail": "Server tidak merespon, proses dihentikan secara paksa."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat menghentikan server: {e}")
    
    raise HTTPException(status_code=404, detail="Server untuk pengguna ini tidak sedang berjalan.")


@router.get("/status", summary="Melihat status server milik pengguna")
def server_status_for_user(current_user: models.User = Depends(auth.get_current_user)):
    """
    Mengecek apakah proses server untuk pengguna yang login ada dan sedang berjalan.
    """
    process = user_processes.get(current_user.username)
    if process and process.poll() is None:
        return {"running": True}
    return {"running": False}

@router.post("/command", summary="Mengirim perintah ke server milik pengguna")
def send_command_to_user_server(
    command: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Mengirimkan string perintah ke stdin dari proses server yang sedang berjalan.
    """
    username = current_user.username
    process = user_processes.get(username)

    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server tidak berjalan, tidak dapat mengirim perintah.")
    
    try:
        # Menulis perintah ke stdin dari proses server, jangan lupa newline
        process.stdin.write(command + '\n')
        process.stdin.flush()
        return {"status": "command_sent", "command": command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengirim perintah: {e}")
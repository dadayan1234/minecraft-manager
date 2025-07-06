import subprocess
import threading
import time
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Annotated
from backend import auth, models
from backend.database import create_connection

router = APIRouter()

# Dictionary untuk mengelola proses dan status tunnel untuk setiap pengguna
# Key: username, Value: {"process": Popen, "status": dict}
user_tunnels = {}

def send_notifications_to_user_webhooks(username: str, url: str):
    """
    Mengambil semua URL webhook milik pengguna dari database dan mengirim notifikasi.
    """
    conn = create_connection()
    if conn is None:
        print("Gagal membuat koneksi ke database.")
        return
    cursor = conn.cursor()
    
    try:
        # Dapatkan semua URL webhook untuk pengguna ini
        cursor.execute("""
            SELECT wh.webhook_url 
            FROM user_webhooks wh
            JOIN users u ON wh.user_id = u.id
            WHERE u.username = ?
        """, (username,))
        
        webhook_urls = [row['webhook_url'] for row in cursor.fetchall()]
    finally:
        conn.close()

    content = f"🎉 Tunnel untuk pengguna **{username}** aktif!\n🔗 Alamat Server: `{url}`"
    
    for webhook_url in webhook_urls:
        try:
            # Mengirim notifikasi secara non-blocking
            with httpx.Client() as client:
                client.post(webhook_url, json={"content": content}, timeout=5)
        except Exception as e:
            print(f"Gagal mengirim webhook ke {webhook_url}: {e}")

def wait_for_ngrok_url(username: str, timeout=20):
    """
    Worker yang berjalan di thread terpisah untuk menunggu URL ngrok muncul dari API lokal.
    """
    time.sleep(2) # Beri waktu agar proses Ngrok dan API-nya sempat berjalan
    for _ in range(timeout):
        try:
            # Ngrok API berjalan di port 4040 secara default
            r = httpx.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
            r.raise_for_status() # Akan error jika status code bukan 2xx
            tunnels_data = r.json().get("tunnels", [])
            
            for t in tunnels_data:
                if t.get("proto") == "tcp" and t.get("public_url"):
                    url = t["public_url"]
                    if username in user_tunnels:
                        user_tunnels[username]["status"] = {"running": True, "url": url}
                        # Jalankan pengiriman notifikasi di thread baru agar tidak memblokir
                        threading.Thread(target=send_notifications_to_user_webhooks, args=(username, url)).start()
                        return
        except httpx.RequestError:
            # API Ngrok mungkin belum siap, coba lagi
            time.sleep(1)
        except Exception as e:
            print(f"Error saat mengambil URL Ngrok untuk {username}: {e}")
            break # Hentikan percobaan jika ada error lain
            
    # Jika loop selesai tanpa menemukan URL
    if username in user_tunnels:
        user_tunnels[username]["status"] = {"running": False, "url": None, "error": "Gagal mendapatkan URL dari Ngrok API."}

@router.post("/tunnel/start", summary="Memulai Ngrok tunnel untuk pengguna")
def start_tunnel_for_user(
    port_data: Annotated[dict, Body(embed=True, example={"port": 25565})],
    current_user: models.User = Depends(auth.get_current_user)
):
    username = current_user.username
    port = port_data.get("port", 25565)
    
    if username in user_tunnels and user_tunnels[username].get("process") and user_tunnels[username]["process"].poll() is None:
        raise HTTPException(status_code=400, detail="Tunnel untuk pengguna ini sudah berjalan.")

    try:
        # Jalankan proses Ngrok. Pastikan 'ngrok' ada di PATH sistem Anda.
        process = subprocess.Popen(
            ["ngrok", "tcp", str(port)],
            stdout=subprocess.DEVNULL, # Sembunyikan output standar
            stderr=subprocess.DEVNULL  # Sembunyikan output error
        )
        
        user_tunnels[username] = {
            "process": process,
            "status": {"running": True, "url": None, "error": None}
        }

        # Jalankan thread untuk memonitor URL tanpa memblokir response API
        threading.Thread(target=wait_for_ngrok_url, args=(username,)).start()

        return {"status": "starting", "detail": "Ngrok tunnel sedang dimulai..."}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Perintah 'ngrok' tidak ditemukan. Pastikan Ngrok terinstall dan ada di PATH sistem Anda.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memulai Ngrok: {e}")

@router.post("/tunnel/stop", summary="Menghentikan Ngrok tunnel milik pengguna")
def stop_tunnel_for_user(current_user: models.User = Depends(auth.get_current_user)):
    username = current_user.username
    tunnel_info = user_tunnels.get(username)

    if tunnel_info and tunnel_info.get("process") and tunnel_info["process"].poll() is None:
        tunnel_info["process"].terminate()
        try:
            # Tunggu sebentar agar proses benar-benar berhenti
            tunnel_info["process"].wait(timeout=5)
        except subprocess.TimeoutExpired:
            tunnel_info["process"].kill() # Paksa berhenti jika terminate gagal
        
        user_tunnels.pop(username, None)
        return {"status": "stopped"}
        
    raise HTTPException(status_code=404, detail="Tunnel untuk pengguna ini tidak sedang berjalan.")

@router.get("/tunnel/status", summary="Melihat status tunnel milik pengguna")
def get_tunnel_status_for_user(current_user: models.User = Depends(auth.get_current_user)):
    username = current_user.username
    tunnel_info = user_tunnels.get(username)

    if not tunnel_info or not tunnel_info.get("process") or tunnel_info["process"].poll() is not None:
        # Jika proses tidak ada atau sudah berhenti, pastikan data lama dibersihkan
        if username in user_tunnels:
            user_tunnels.pop(username, None)
        return {"running": False, "url": None}
    
    # Kembalikan status terakhir yang disimpan oleh thread worker
    return user_tunnels[username].get("status", {"running": True, "url": None})
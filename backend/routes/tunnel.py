import subprocess
import threading
import asyncio
import time
from fastapi import APIRouter, WebSocket, Request
from fastapi.responses import JSONResponse
import httpx
from backend.routes.websocket import tunnel_clients  # ← kita gunakan array global tunnel_clients


DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1390165991081771018/AZmWeABt8m3g7zwKIcGEltW_Z1HlZlsdEw1IIFYxy1xPCQSVDFrss2IQl05aIqWy01Xr"  # ← ganti dengan milikmu


router = APIRouter()

ngrok_process = None
ngrok_output = []
ngrok_status = {"running": False, "url": None}


@router.post("/tunnel/start")
async def start_tunnel(request: Request):
    global ngrok_process, ngrok_output, ngrok_status
    data = await request.json()
    port = str(data.get("port", 25565))

    if ngrok_process and ngrok_process.poll() is None:
        return JSONResponse(content={"status": "already running", "url": ngrok_status["url"]})

    ngrok_output.clear()
    ngrok_status = {"running": True, "url": None}

    # Jalankan ngrok (tanpa baca outputnya langsung)
    ngrok_process = subprocess.Popen(
        ["ngrok", "tcp", port],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Tunggu URL muncul dari web API
    threading.Thread(target=wait_for_ngrok_url_and_broadcast, daemon=True).start()

    return {"status": "starting"}

def wait_for_ngrok_url_and_broadcast(timeout=15):
    global ngrok_status
    for _ in range(timeout):
        try:
            r = httpx.get("http://127.0.0.1:4040/api/tunnels")
            tunnels = r.json().get("tunnels", [])
            for t in tunnels:
                if t["proto"] == "tcp":
                    url = t["public_url"]
                    ngrok_status["url"] = url
                    ngrok_output.append(f"🔗 Tunnel URL: {url}")
                    ngrok_output.append("✅ Tunnel started successfully.")
                    send_discord_webhook(url)
                    asyncio.run(broadcast_to_tunnel_clients(f"🔗 Tunnel URL: {url}"))
                    return
        except Exception:
            pass
        time.sleep(1)
    ngrok_output.append("❌ Tunnel failed to start.")
    asyncio.run(broadcast_to_tunnel_clients("❌ Tunnel failed to start."))


async def broadcast_to_tunnel_clients(message: str):
    for client in tunnel_clients.copy():
        try:
            await client.send_text(message)
        except:
            tunnel_clients.remove(client)

def read_ngrok_output():
    global ngrok_process, ngrok_output, ngrok_status
    if ngrok_process and ngrok_process.stdout:
        for line in ngrok_process.stdout:
            clean_line = line.strip()
            ngrok_output.append(clean_line)

            # Broadcast ke semua WebSocket tunnel clients
            asyncio.run(broadcast_to_tunnel_clients(clean_line))

            if "tcp://" in clean_line and not ngrok_status["url"]:
                start = clean_line.find("tcp://")
                end = clean_line.find(" ", start)
                if start != -1:
                    ngrok_status["url"] = clean_line[start:] if end == -1 else clean_line[start:end]
                    send_discord_webhook(ngrok_status["url"])
                    
def send_discord_webhook(url: str):
    try:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": f"🔗 Tunnel URL updated: `{url}`"})
    except Exception as e:
        print("Discord webhook failed:", e)


@router.post("/tunnel/stop")
def stop_tunnel():
    global ngrok_process, ngrok_status
    if ngrok_process and ngrok_process.poll() is None:
        ngrok_process.terminate()
        ngrok_process = None
        ngrok_status = {"running": False, "url": None}
        return {"status": "stopped"}
    return {"status": "not running"}


@router.get("/tunnel/status")
def get_tunnel_status():
    global ngrok_status, ngrok_process

    if ngrok_process and ngrok_process.poll() is None:
        # Proses ngrok masih hidup
        ngrok_status["running"] = True

        # Coba ambil URL dari API
        try:
            r = httpx.get("http://127.0.0.1:4040/api/tunnels")
            tunnels = r.json().get("tunnels", [])
            for t in tunnels:
                if t["proto"] == "tcp":
                    ngrok_status["url"] = t["public_url"]
                    break
        except:
            pass
    else:
        ngrok_status["running"] = False
        ngrok_status["url"] = None

    return ngrok_status



@router.websocket("/ws/tunnel")
async def tunnel_logs(websocket: WebSocket):
    await websocket.accept()
    tunnel_clients.append(websocket)

    try:
        # Kirim seluruh log yang sudah ada
        for line in ngrok_output:
            await websocket.send_text(line)

        # Kirim log baru jika ada
        while True:
            await asyncio.sleep(1)
    except Exception:
        if websocket in tunnel_clients:
            tunnel_clients.remove(websocket)

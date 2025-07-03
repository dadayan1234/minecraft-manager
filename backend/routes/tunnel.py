import subprocess
import threading
import asyncio
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

    ngrok_process = subprocess.Popen(
        ["ngrok", "tcp", port],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    threading.Thread(target=read_ngrok_output, daemon=True).start()

    return {"status": "starting"}

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
                    
def send_discord_webhook(url):
    try:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": f"🔗 Tunnel URL updated: `{url}`"})
    except Exception as e:
        print("Failed to send webhook:", e)


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
    return ngrok_status


@router.websocket("/ws/tunnel")
async def tunnel_logs(websocket: WebSocket):
    await websocket.accept()
    sent_index = 0
    try:
        while True:
            if sent_index < len(ngrok_output):
                await websocket.send_text(ngrok_output[sent_index])
                sent_index += 1
            await asyncio.sleep(1)
    except Exception as e:
        print("Tunnel WebSocket closed:", e)

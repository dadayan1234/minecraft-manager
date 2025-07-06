from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend import auth, models
# Impor dictionary proses dari server.py untuk mengakses proses yang sedang berjalan
from .server import user_processes 

router = APIRouter()

class Command(BaseModel):
    command: str

@router.post("/", summary="Mengirim perintah ke konsol server milik pengguna")
def send_command_to_user_server(
    cmd: Command,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Mengirimkan string perintah ke stdin dari proses server pengguna yang sedang berjalan.
    """
    username = current_user.username
    process = user_processes.get(username)

    # Cek apakah server milik pengguna ini sedang berjalan
    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server untuk pengguna ini tidak sedang berjalan.")
    
    try:
        # Menulis perintah ke Standard Input dari proses server
        # Tambahkan newline agar perintah dieksekusi
        process.stdin.write(cmd.command + '\n')
        process.stdin.flush() # Pastikan perintah langsung dikirim
        
        # Catatan: Mendapatkan output langsung dari command di sini rumit.
        # Output akan muncul di stream log WebSocket.
        return {"status": "command_sent", "command": cmd.command}
    except Exception as e:
        # Menangani error jika pipe rusak (misal, server crash)
        raise HTTPException(status_code=500, detail=f"Gagal mengirim perintah: {str(e)}")
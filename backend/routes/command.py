from fastapi import APIRouter, Depends, HTTPException
from backend import models
from backend.dependencies import get_server_details
from backend.shared_state import server_processes # <-- PERBAIKAN: Impor dari file 'shared_state.py' yang netral

router = APIRouter()

@router.post("/servers/{server_id}/command", summary="Mengirim perintah ke server spesifik")
def send_command(
    command_data: models.Command,
    server_details: dict = Depends(get_server_details)
):
    """
    Mengirimkan string perintah ke stdin dari proses server yang sedang berjalan,
    berdasarkan server_id yang diberikan.
    """
    server_id = server_details['id']
    process = server_processes.get(server_id)

    # Cek apakah proses untuk server ini ada dan sedang berjalan
    if not process or process.poll() is not None:
        raise HTTPException(status_code=404, detail="Server tidak berjalan atau tidak ditemukan.")
        
    try:
        # Menulis perintah ke proses server yang benar
        process.stdin.write(command_data.command + '\n')
        process.stdin.flush()
        return {"status": "command_sent", "server_id": server_id, "command": command_data.command}
    except Exception as e:
        # Menangani error jika terjadi masalah saat menulis ke proses
        raise HTTPException(status_code=500, detail=f"Gagal mengirim perintah: {str(e)}")
from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel
from typing import List, Optional
from backend import auth, models
from backend.database import create_connection

router = APIRouter()
MOJANG_VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

class ServerVersion(BaseModel):
    id: str
    type: str
    url: str
    releaseTime: str

class VersionSelect(BaseModel):
    version: str

@router.get("/server/versions", response_model=List[ServerVersion], summary="Mendapatkan daftar versi Minecraft yang tersedia")
async def get_available_versions():
    """
    Mengambil daftar versi rilis (release) resmi dari manifest Mojang.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(MOJANG_VERSION_MANIFEST_URL)
            response.raise_for_status()
            data = response.json()
            # Kita hanya akan menampilkan versi rilis (release) agar tidak terlalu banyak
            return [v for v in data.get("versions", []) if v.get("type") == "release"]
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Tidak dapat menghubungi server Mojang: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan: {e}")

@router.post("/server/version", summary="Menetapkan versi server untuk pengguna")
def set_user_server_version(
    version_data: VersionSelect,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Menyimpan preferensi versi server pengguna ke database."""
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Gagal terhubung ke database.")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET server_version = ? WHERE username = ?",
            (version_data.version, current_user.username)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan.")
        return {"status": "success", "message": f"Versi server untuk {current_user.username} diatur ke {version_data.version}"}
    finally:
        conn.close()
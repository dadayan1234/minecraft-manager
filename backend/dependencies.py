from fastapi import Depends, HTTPException, Path
from typing import Annotated
from . import auth, models
from .database import create_connection

def get_server_details(
    server_id: Annotated[int, Path(title="The ID of the server to operate on.")],
    current_user: models.User = Depends(auth.get_current_user)
) -> dict:
    """
    Dependency yang memverifikasi kepemilikan server dan mengembalikan detailnya.
    Fungsi ini sekarang berada di lokasi netral untuk menghindari impor sirkular.
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
    
    # Mengonversi sqlite3.Row menjadi dictionary
    return dict(server_data)
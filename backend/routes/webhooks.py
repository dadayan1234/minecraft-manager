from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List
from backend import auth, models
from backend.database import create_connection

router = APIRouter()

class Webhook(BaseModel):
    id: int
    webhook_url: HttpUrl

class WebhookCreate(BaseModel):
    webhook_url: HttpUrl

@router.post("/webhooks", response_model=Webhook, summary="Menambahkan URL webhook baru untuk pengguna")
def add_webhook(
    webhook_data: WebhookCreate,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Menyimpan URL webhook baru ke database untuk pengguna yang sedang login."""
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    # Dapatkan user_id dari username
    cursor.execute("SELECT id FROM users WHERE username = ?", (current_user.username,))
    user_row = cursor.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    user_id = user_row['id']

    cursor.execute(
        "INSERT INTO user_webhooks (user_id, webhook_url) VALUES (?, ?)",
        (user_id, str(webhook_data.webhook_url))
    )
    new_webhook_id = cursor.lastrowid
    if new_webhook_id is None:
        conn.close()
        raise HTTPException(status_code=500, detail="Failed to retrieve new webhook ID")
    conn.commit()
    conn.close()
    
    return Webhook(id=new_webhook_id, webhook_url=webhook_data.webhook_url)

@router.get("/webhooks", response_model=List[Webhook], summary="Melihat semua URL webhook milik pengguna")
def list_webhooks(current_user: models.User = Depends(auth.get_current_user)):
    """Mengambil semua URL webhook yang telah ditambahkan oleh pengguna."""
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (current_user.username,))
    user_row = cursor.fetchone()
    user_id = user_row['id']

    cursor.execute("SELECT id, webhook_url FROM user_webhooks WHERE user_id = ?", (user_id,))
    webhooks = [Webhook(id=row['id'], webhook_url=row['webhook_url']) for row in cursor.fetchall()]
    conn.close()
    return webhooks

@router.delete("/webhooks/{webhook_id}", status_code=204, summary="Menghapus URL webhook")
def delete_webhook(
    webhook_id: int,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Menghapus URL webhook spesifik milik pengguna."""
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (current_user.username,))
    user_row = cursor.fetchone()
    user_id = user_row['id']
    
    # Verifikasi bahwa webhook yang akan dihapus adalah milik pengguna yang benar
    cursor.execute(
        "DELETE FROM user_webhooks WHERE id = ? AND user_id = ?",
        (webhook_id, user_id)
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook tidak ditemukan atau bukan milik Anda")
    
    conn.commit()
    conn.close()
    return
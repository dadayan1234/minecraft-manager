from pydantic import BaseModel, HttpUrl
from typing import Optional, List

# --- Model untuk Otentikasi dan Pengguna ---

class User(BaseModel):
    """
    Model dasar untuk data pengguna yang bisa ditampilkan secara publik.
    """
    username: str
    
class UserInDB(User):
    """
    Model pengguna yang menyertakan data sensitif (password hash) untuk penggunaan internal.
    """
    hashed_password: str

class UserCreate(BaseModel):
    """
    Model untuk membuat pengguna baru (registrasi).
    """
    username: str
    password: str

class Token(BaseModel):
    """
    Model untuk respons token JWT setelah login berhasil.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Model untuk data yang terkandung di dalam payload token JWT.
    """
    username: Optional[str] = None


# --- Model untuk Manajemen Server ---

class ServerCreate(BaseModel):
    """
    Model untuk membuat instance server baru.
    """
    name: str
    version: str

class ServerInfo(BaseModel):
    """
    Model untuk menampilkan informasi dasar tentang sebuah server.
    """
    id: int
    name: str
    version: str

class VersionSelect(BaseModel):
    """
    Model untuk menetapkan versi server.
    """
    version: str

class ServerVersion(BaseModel):
    """
    Model untuk data versi yang diambil dari Mojang.
    """
    id: str
    type: str
    url: str
    releaseTime: str
    

# --- Model untuk Fitur Lain ---

class Command(BaseModel):
    """
    Model untuk menerima perintah yang akan dijalankan di server.
    """
    command: str

class Webhook(BaseModel):
    """
    Model untuk menampilkan data webhook.
    """
    id: int
    webhook_url: HttpUrl

class WebhookCreate(BaseModel):
    """
    Model untuk membuat webhook baru.
    """
    webhook_url: HttpUrl
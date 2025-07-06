
from fastapi import Request, HTTPException
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import sqlite3
from backend.models import TokenData, User
from backend.database import create_connection

TOKEN = "supersecret"

def check_token(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

SECRET_KEY = "McNggoS1te"  # Ganti dengan kunci rahasia yang kuat
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db, username: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    if user_data:
        return {"username": user_data[1], "hashed_password": user_data[2], "server_path": user_data[3]}
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=str(username))
    except JWTError:
        raise credentials_exception
    
    conn = create_connection()
    if token_data.username is None:
        raise credentials_exception
    user = get_user(conn, username=token_data.username)
    if conn is not None:
        conn.close()

    if user is None:
        raise credentials_exception
    return User(**user)

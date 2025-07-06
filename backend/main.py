from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from backend.routes import filemanager, server, command, config, tunnel, websocket
from backend.database import initialize_database, create_connection
from backend import auth, models
from datetime import timedelta
from backend.routes import webhooks
from backend.routes import versions

# Inisialisasi database saat aplikasi dimulai
initialize_database()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint untuk registrasi pengguna baru
@app.post("/register", response_model=models.User)
def register_user(user: models.UserCreate):
    conn = create_connection()
    if db_user := auth.get_user(conn, user.username):
        if conn:
            conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    # Anda bisa mengatur path default di sini
    default_server_path = f"servers/{user.username}"
    
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, hashed_password, server_path) VALUES (?, ?, ?)",
        (user.username, hashed_password, default_server_path)
    )
    conn.commit()
    conn.close()
    
    return models.User(username=user.username, server_path=default_server_path)

# Endpoint untuk login dan mendapatkan token
@app.post("/token", response_model=models.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = create_connection()
    user = auth.get_user(conn, form_data.username)
    if conn:
        conn.close()
    if not user or not auth.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Melindungi router yang ada dengan otentikasi
# Perhatikan penambahan `dependencies=[Depends(auth.get_current_user)]`
app.include_router(versions.router, dependencies=[Depends(auth.get_current_user)])
app.include_router(webhooks.router, dependencies=[Depends(auth.get_current_user)])
app.include_router(filemanager.router, prefix="/files", dependencies=[Depends(auth.get_current_user)])
app.include_router(server.router, prefix="/server", dependencies=[Depends(auth.get_current_user)])
app.include_router(command.router, prefix="/cmd", dependencies=[Depends(auth.get_current_user)])
app.include_router(config.router, prefix="/config", dependencies=[Depends(auth.get_current_user)])
app.include_router(tunnel.router, prefix="/tunnel", dependencies=[Depends(auth.get_current_user)])

# Websocket tidak bisa menggunakan dependency di router, otentikasi harus ditangani di dalam endpoint
app.include_router(websocket.router)
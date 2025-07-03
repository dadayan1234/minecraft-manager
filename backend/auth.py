
from fastapi import Request, HTTPException

TOKEN = "supersecret"

def check_token(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized")

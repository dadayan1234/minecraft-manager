from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    server_path: Optional[str] = None
    filemanager_path: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
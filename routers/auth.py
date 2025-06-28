from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from datetime import datetime, timedelta
from db import supabase
from fastapi import status
from dotenv import load_dotenv
import os
import jwt

load_dotenv()

router = APIRouter()

# Configs
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")  # Default for dev
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# Models
class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

# Helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Routes
@router.post("/signup")
def signup(user: User):
    existing = supabase.table("users").select("*").eq("username", user.username).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    hashed_password = pwd_context.hash(user.password)
    result = supabase.table("users").insert({
        "username": user.username,
        "password": hashed_password
    }).execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")

    return {"msg": "User created", "user": result.data[0]["username"]}

@router.post("/login")
def login(user: User):
    result = supabase.table("users").select("*").eq("username", user.username).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    stored_user = result.data[0]
    if not pwd_context.verify(user.password, stored_user["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from db import supabase
from fastapi import status
from dotenv import load_dotenv
import os
import jwt as PyJWT
from models.users import UserRole

load_dotenv()

router = APIRouter()

# Configs
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")  # Default for dev
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# Models
class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str
    last_name: str
    role: UserRole = UserRole.PATIENT

# Helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return PyJWT.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Routes
@router.post("/signup")
def signup(user: UserRegistration):
    # Check for existing username
    existing = supabase.table("users").select("*").eq("username", user.username).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    # Check for existing email
    existing_email = supabase.table("users").select("*").eq("email", user.email).execute()
    if existing_email.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    
    # Create user in database
    result = supabase.table("users").insert({
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role
    }).execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    
    # Create role-specific profile
    user_id = result.data[0]["id"]
    if user.role == UserRole.PATIENT:
        supabase.table("patient_profiles").insert({"user_id": user_id}).execute()
    elif user.role == UserRole.DOCTOR:
        supabase.table("doctor_profiles").insert({"user_id": user_id}).execute()

    return {"msg": "User created", "user": result.data[0]["username"]}

@router.post("/login")
def login(user: UserLogin):
    result = supabase.table("users").select("*").eq("username", user.username).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    stored_user = result.data[0]
    if not pwd_context.verify(user.password, stored_user["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "role": stored_user["role"]}
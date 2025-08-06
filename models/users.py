from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.PATIENT

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
class UserProfile(UserBase):
    id: str
    
    class Config:
        orm_mode = True

class PatientProfile(BaseModel):
    user_id: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None

class DoctorProfile(BaseModel):
    user_id: str
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    experience_years: Optional[int] = None

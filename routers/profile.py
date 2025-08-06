from fastapi import APIRouter, Depends, HTTPException, status
from typing import Union
from models.users import PatientProfile, DoctorProfile, UserProfile, UserUpdate, UserRole
from middleware.auth import get_current_user
from db import supabase
from models.responses import BaseResponse

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_user_profile(username: str = Depends(get_current_user)):
    """Get current user profile"""
    result = supabase.table("users").select("*").eq("username", username).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    user = result.data[0]
    return user

@router.put("/update", response_model=BaseResponse)
async def update_user_profile(user_data: UserUpdate, username: str = Depends(get_current_user)):
    """Update user profile information"""
    update_data = {k: v for k, v in user_data.dict().items() if v is not None}
    
    if not update_data:
        return BaseResponse(success=True, message="No changes to update")
    
    result = supabase.table("users").update(update_data).eq("username", username).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")
    
    return BaseResponse(success=True, message="Profile updated successfully", data=result.data[0])

@router.get("/patient-details", response_model=Union[PatientProfile, dict])
async def get_patient_details(username: str = Depends(get_current_user)):
    """Get patient specific profile details"""
    # First check if user is a patient
    user_result = supabase.table("users").select("id, role").eq("username", username).execute()
    
    if not user_result.data or user_result.data[0]["role"] != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to patients")
    
    user_id = user_result.data[0]["id"]
    
    # Get patient details
    result = supabase.table("patient_profiles").select("*").eq("user_id", user_id).execute()
    
    if not result.data:
        # Return empty profile if not found
        return {"user_id": user_id}
    
    return result.data[0]

@router.put("/patient-details", response_model=BaseResponse)
async def update_patient_details(profile: PatientProfile, username: str = Depends(get_current_user)):
    """Update patient specific profile details"""
    # First check if user is a patient
    user_result = supabase.table("users").select("id, role").eq("username", username).execute()
    
    if not user_result.data or user_result.data[0]["role"] != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to patients")
    
    user_id = user_result.data[0]["id"]
    profile_dict = profile.dict()
    profile_dict["user_id"] = user_id
    
    # Check if profile exists
    check_result = supabase.table("patient_profiles").select("user_id").eq("user_id", user_id).execute()
    
    if not check_result.data:
        # Create new profile
        result = supabase.table("patient_profiles").insert(profile_dict).execute()
    else:
        # Update existing profile
        result = supabase.table("patient_profiles").update(profile_dict).eq("user_id", user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update patient profile")
    
    return BaseResponse(success=True, message="Patient profile updated successfully", data=result.data[0])

@router.get("/doctor-details", response_model=Union[DoctorProfile, dict])
async def get_doctor_details(username: str = Depends(get_current_user)):
    """Get doctor specific profile details"""
    # First check if user is a doctor
    user_result = supabase.table("users").select("id, role").eq("username", username).execute()
    
    if not user_result.data or user_result.data[0]["role"] != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to doctors")
    
    user_id = user_result.data[0]["id"]
    
    # Get doctor details
    result = supabase.table("doctor_profiles").select("*").eq("user_id", user_id).execute()
    
    if not result.data:
        # Return empty profile if not found
        return {"user_id": user_id}
    
    return result.data[0]

@router.put("/doctor-details", response_model=BaseResponse)
async def update_doctor_details(profile: DoctorProfile, username: str = Depends(get_current_user)):
    """Update doctor specific profile details"""
    # First check if user is a doctor
    user_result = supabase.table("users").select("id, role").eq("username", username).execute()
    
    if not user_result.data or user_result.data[0]["role"] != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to doctors")
    
    user_id = user_result.data[0]["id"]
    profile_dict = profile.dict()
    profile_dict["user_id"] = user_id
    
    # Check if profile exists
    check_result = supabase.table("doctor_profiles").select("user_id").eq("user_id", user_id).execute()
    
    if not check_result.data:
        # Create new profile
        result = supabase.table("doctor_profiles").insert(profile_dict).execute()
    else:
        # Update existing profile
        result = supabase.table("doctor_profiles").update(profile_dict).eq("user_id", user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update doctor profile")
    
    return BaseResponse(success=True, message="Doctor profile updated successfully", data=result.data[0])

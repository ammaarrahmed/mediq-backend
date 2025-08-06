from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from models.responses import BaseResponse
from middleware.auth import get_current_user
from db import supabase
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import requests
from uuid import uuid4

router = APIRouter()

class MedicalAnalysisRequest(BaseModel):
    document_id: Optional[str] = None
    symptoms: List[str]
    duration: Optional[int] = None  # duration in days
    severity: Optional[int] = None  # 1-10 scale
    additional_notes: Optional[str] = None

class DiagnosticQuestion(BaseModel):
    question: str
    context: str

@router.post("/analyze-symptoms", response_model=BaseResponse)
async def analyze_symptoms(request: MedicalAnalysisRequest, username: str = Depends(get_current_user)):
    """Analyze symptoms and provide diagnostic guidance"""
    
    # Get user information to provide context
    user = supabase.table("users").select("*").eq("username", username).execute().data[0]
    
    # Get patient profile if exists
    medical_context = ""
    if user["role"] == "patient":
        patient_profile = supabase.table("patient_profiles").select("*").eq("user_id", user["id"]).execute()
        if patient_profile.data:
            profile = patient_profile.data[0]
            if profile.get("medical_history"):
                medical_context += f"Medical History: {profile['medical_history']}\n"
            if profile.get("allergies"):
                medical_context += f"Allergies: {profile['allergies']}\n"
            if profile.get("current_medications"):
                medical_context += f"Current Medications: {profile['current_medications']}\n"
    
    # Get the document text if a document ID was provided
    document_text = ""
    if request.document_id:
        doc = supabase.table("documents").select("*").eq("id", request.document_id).eq("user_id", username).execute()
        if doc.data:
            document_text = doc.data[0].get("text", "")
    
    # Prepare the prompt for medical analysis
    prompt = f"""
As an AI Health Assistant, please analyze the following symptoms:
- {', '.join(request.symptoms)}

Additional information:
- Duration: {request.duration or 'Not specified'} days
- Severity (1-10): {request.severity or 'Not specified'}
- Additional notes: {request.additional_notes or 'None'}

{medical_context if medical_context else ''}

{f"Relevant medical document: {document_text[:500]}..." if document_text else ''}

Based on the information provided:
1. What are the possible conditions that might explain these symptoms?
2. What additional symptoms should I watch for?
3. What home care measures might help?
4. When should I seek immediate medical attention?
5. What diagnostic tests might a doctor recommend?

IMPORTANT DISCLAIMER: This is an AI analysis and should not replace professional medical advice. Always consult with a healthcare provider for proper diagnosis and treatment.
    """
    
    # Call OpenRouter API for analysis
    from routers.chat import call_openrouter_model
    
    try:
        analysis = call_openrouter_model(document_text[:1000] if document_text else "", prompt)
        
        # Save analysis to database
        analysis_id = str(uuid4())
        supabase.table("medical_analyses").insert({
            "id": analysis_id,
            "user_id": username,
            "symptoms": request.symptoms,
            "analysis": analysis,
            "document_id": request.document_id
        }).execute()
        
        return BaseResponse(
            success=True,
            message="Symptoms analyzed successfully",
            data={
                "analysis_id": analysis_id,
                "analysis": analysis
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze symptoms: {str(e)}")

@router.post("/follow-up-questions", response_model=BaseResponse)
async def generate_follow_up_questions(analysis_id: str, username: str = Depends(get_current_user)):
    """Generate follow-up questions based on a previous analysis"""
    
    # Get the analysis
    analysis = supabase.table("medical_analyses").select("*").eq("id", analysis_id).eq("user_id", username).execute()
    
    if not analysis.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis_text = analysis.data[0].get("analysis", "")
    
    prompt = f"""
Based on the previous medical analysis:

{analysis_text}

Generate 3-5 important follow-up questions that would help clarify the situation or improve the analysis. 
These questions should be specific and help gather clinically relevant information that was missing from the initial consultation.
    """
    
    # Call OpenRouter API for follow-up questions
    from routers.chat import call_openrouter_model
    
    try:
        questions = call_openrouter_model("", prompt)
        
        return BaseResponse(
            success=True,
            message="Follow-up questions generated successfully",
            data={
                "questions": questions
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up questions: {str(e)}")

@router.post("/summarize-history", response_model=BaseResponse)
async def summarize_medical_history(username: str = Depends(get_current_user)):
    """Summarize patient's medical history from documents and past analyses"""
    
    # Get all documents
    documents = supabase.table("documents").select("*").eq("user_id", username).execute().data
    
    # Get all analyses
    analyses = supabase.table("medical_analyses").select("*").eq("user_id", username).execute().data
    
    # Get patient profile
    user = supabase.table("users").select("*").eq("username", username).execute().data[0]
    patient_profile = None
    if user["role"] == "patient":
        profile_data = supabase.table("patient_profiles").select("*").eq("user_id", user["id"]).execute().data
        if profile_data:
            patient_profile = profile_data[0]
    
    # Prepare context for summarization
    document_texts = []
    for doc in documents:
        text = doc.get("text", "")
        if text:
            document_texts.append(text[:500])  # Take first 500 chars of each document
    
    analysis_texts = []
    for analysis in analyses:
        analysis_text = analysis.get("analysis", "")
        if analysis_text:
            analysis_texts.append(analysis_text[:500])  # Take first 500 chars of each analysis
    
    context = "\n\n".join(document_texts + analysis_texts)
    
    # Add profile information if available
    profile_context = ""
    if patient_profile:
        if patient_profile.get("medical_history"):
            profile_context += f"Self-reported medical history: {patient_profile['medical_history']}\n"
        if patient_profile.get("allergies"):
            profile_context += f"Allergies: {patient_profile['allergies']}\n"
        if patient_profile.get("current_medications"):
            profile_context += f"Current medications: {patient_profile['current_medications']}\n"
    
    # Generate summary prompt
    prompt = f"""
As a medical AI assistant, please create a comprehensive summary of the patient's medical history based on the following information:

{profile_context}

Documents and past consultations:
{context[:3000]}  # Limit to avoid token limits

Please provide:
1. A chronological summary of key medical events
2. Consistent symptoms or complaints
3. Any diagnosed conditions
4. Current medications and treatments
5. Areas that may require follow-up or clarification

This summary should help healthcare providers quickly understand the patient's medical background.
    """
    
    # Call OpenRouter API for summary
    from routers.chat import call_openrouter_model
    
    try:
        summary = call_openrouter_model("", prompt)
        
        # Save summary to database
        summary_id = str(uuid4())
        supabase.table("medical_summaries").insert({
            "id": summary_id,
            "user_id": username,
            "summary": summary
        }).execute()
        
        return BaseResponse(
            success=True,
            message="Medical history summarized successfully",
            data={
                "summary_id": summary_id,
                "summary": summary
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize medical history: {str(e)}")

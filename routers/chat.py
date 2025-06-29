import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import supabase
import uuid
import os

router = APIRouter()

# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/completion"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Set your OpenRouter API key as an environment variable

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

def call_openrouter_model(document: str, user_message: str) -> str:
    """Call OpenRouter API to generate a chat response."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "claude-2",  # Claude is cheap, efficient, and great for conversational tasks
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Use the provided document to answer the user's questions."},
            {"role": "system", "content": f"Document: {document}"},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 500,  # Limit tokens to control cost
        "temperature": 0.7
    }

    response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error from OpenRouter API: {response.text}")
    
    result = response.json()
    return result["choices"][0]["message"]["content"]  # Adjust based on API response structure

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # Enforce a document size limit to avoid API issues
    if len(data.document_text) > 10000:  # Limit to 10,000 characters
        raise HTTPException(status_code=400, detail="Document too large. Please limit to 10,000 characters.")
    
    # Call OpenRouter to generate a response
    response = call_openrouter_model(data.document_text, data.user_message)

    # Save both messages to Supabase for chat history
    supabase.table("chat_messages").insert([
        {
            "id": str(uuid.uuid4()),
            "session_id": data.session_id,
            "role": "user",
            "content": data.user_message
        },
        {
            "id": str(uuid.uuid4()),
            "session_id": data.session_id,
            "role": "assistant",
            "content": response
        }
    ]).execute()

    return {"response": response}

@router.get("/history/{session_id}")
def get_chat_history(session_id: str):
    # Retrieve chat history from Supabase
    result = supabase.table("chat_messages") \
        .select("role, content, created_at") \
        .eq("session_id", session_id) \
        .order("created_at", desc=False) \
        .execute()
    return result.data
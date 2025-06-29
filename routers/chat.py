import requests
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import supabase  # Ensure Supabase client is properly configured in the db module
import uuid
import os

router = APIRouter()

# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
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
        "Content-Type": "application/json",
    }
    payload = {
        "model": "anthropic/claude-2.0",  # Use the desired model
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Use the provided document to answer the user's questions."},
            {"role": "system", "content": f"Document: {document}"},
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(
        url=OPENROUTER_API_URL,
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error from OpenRouter API: {response.text}")

    try:
        result = response.json()
        return result["choices"][0]["message"]["content"]  # Adjust based on API response structure
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenRouter response: {e}")

def create_chat_session(session_id: str):
    """Create a new chat session in Supabase."""
    try:
        supabase.table("chat_sessions").insert([
            {
                "id": session_id,
                "started_at": "now()",  # Supabase will handle the timestamp
            }
        ]).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {e}")

def save_message_to_supabase(session_id: str, role: str, content: str):
    """Save a chat message to Supabase."""
    try:
        supabase.table("chat_messages").insert([
            {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "role": role,
                "content": content,
                "started_at": "now()"  # Supabase will handle the timestamp
            }
        ]).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat message: {e}")

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # Enforce a document size limit to avoid API issues
    if len(data.document_text) > 10000:  # Limit to 10,000 characters
        raise HTTPException(status_code=400, detail="Document too large. Please limit to 10,000 characters.")

    # Create a new chat session if it doesn't already exist
    create_chat_session(data.session_id)

    # Save the user's message to Supabase
    save_message_to_supabase(data.session_id, "user", data.user_message)

    # Call OpenRouter to generate a response
    response = call_openrouter_model(data.document_text, data.user_message)

    # Save the assistant's response to Supabase
    save_message_to_supabase(data.session_id, "assistant", response)

    # Return the response to the client
    return {"response": response}
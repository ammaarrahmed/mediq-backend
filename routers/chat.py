import requests
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from db import supabase  # Ensure Supabase client is properly configured in the db module
import uuid
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from middleware.auth import get_current_user
from models.responses import BaseResponse

router = APIRouter()

# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Set your OpenRouter API key as an environment variable

# Models
class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # Optional to allow auto-generation
    document_text: Optional[str] = None
    user_message: str
    document_id: Optional[str] = None
    include_document_context: bool = True

class ChatSession(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    document_id: Optional[str] = None
    
class ChatHistoryRequest(BaseModel):
    session_id: str
    limit: int = 50
    offset: int = 0
    
class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    document_id: Optional[str] = None
    
class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    ended_at: Optional[bool] = None  # True to end the session 

def get_chat_history(session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get chat history for a specific session"""
    try:
        result = supabase.table("chat_messages") \
            .select("*") \
            .eq("session_id", session_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .offset(offset) \
            .execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {e}")

def get_user_chat_sessions(username: str) -> List[Dict[str, Any]]:
    """Get all chat sessions for a user"""
    try:
        result = supabase.table("chat_sessions") \
            .select("*") \
            .eq("user_id", username) \
            .order("updated_at", desc=True) \
            .execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat sessions: {e}")

def check_session_exists(session_id: str, username: str) -> bool:
    """Check if a session exists and belongs to the user"""
    try:
        result = supabase.table("chat_sessions") \
            .select("id") \
            .eq("id", session_id) \
            .eq("user_id", username) \
            .execute()
        return len(result.data) > 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check session: {e}")

def call_openrouter_model(document: str, user_message: str, history: List[Dict[str, str]] = None) -> str:
    """Call OpenRouter API to generate a chat response using Mistral 7B Instruct."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Start with system messages
    messages = [
        {"role": "system", "content": "You are MedIQ, an advanced medical assistant. Help users understand medical information, analyze symptoms, interpret medical documents, and provide reliable health information. Always maintain a professional, empathetic tone. Remind users that you are an AI and cannot provide definitive medical diagnoses, and they should consult healthcare professionals for proper medical advice."}
    ]
    
    # Add document context if provided
    if document and document.strip():
        messages.append({"role": "system", "content": f"Document: {document[:5000]}"})  # Limit document size
    
    # Add conversation history
    if history and len(history) > 0:
        messages.extend(history)
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": "mistralai/mistral-7b-instruct",  # Using Mistral 7B Instruct
        "messages": messages,
        "temperature": 0.7,  # Add some controlled randomness
        "max_tokens": 1000   # Limit response length
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

def create_chat_session(session_id: str, username: str, title: str = None, document_id: str = None) -> Dict[str, Any]:
    """Create a new chat session in Supabase."""
    try:
        session_data = {
            "id": session_id,
            "user_id": username,
            "started_at": "now()",  # Supabase will handle the timestamp
        }
        
        if title:
            session_data["title"] = title
            
        if document_id:
            session_data["document_id"] = document_id
            
        result = supabase.table("chat_sessions").insert(session_data).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {e}")
def save_message_to_supabase(session_id: str, role: str, content: str) -> Dict[str, Any]:
    """Save a chat message to Supabase."""
    try:
        message_id = str(uuid.uuid4())
        result = supabase.table("chat_messages").insert({
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": "now()"  # Supabase will handle the timestamp
        }).execute()
        
        # Also update the last_message field in the session
        if role == "user":
            supabase.table("chat_sessions").update({
                "last_message": content[:100],  # First 100 chars of message
                "updated_at": "now()"
            }).eq("id", session_id).execute()
            
        return result.data[0] if result.data else {"id": message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat message: {e}")

@router.post("/chat")
async def chat_endpoint(data: ChatRequest, username: str = Depends(get_current_user)):
    """Chat with the AI assistant"""
    # Set default values if needed
    document_text = data.document_text or ""
    
    # Enforce a document size limit to avoid API issues
    if document_text and len(document_text) > 10000:  # Limit to 10,000 characters
        raise HTTPException(status_code=400, detail="Document too large. Please limit to 10,000 characters.")

    # Generate a new UUID for the session if not provided
    session_id = data.session_id or str(uuid.uuid4())
    is_new_session = not data.session_id

    # Create a new chat session if it's a new session
    if is_new_session:
        title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        create_chat_session(session_id, username, title, data.document_id)

    # Get chat history if this is an existing session
    chat_history = []
    history_for_api = []
    if not is_new_session:
        # Check if the session exists and belongs to the user
        if not check_session_exists(session_id, username):
            raise HTTPException(status_code=403, detail="Chat session not found or access denied")
        
        # Get previous messages
        chat_history = get_chat_history(session_id, limit=10)  # Last 10 messages
        
        # Format history for the API
        history_for_api = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in chat_history
        ]
    
    # Save the user's message to Supabase
    user_msg = save_message_to_supabase(session_id, "user", data.user_message)

    # Call OpenRouter to generate a response, providing conversation history
    response = call_openrouter_model(document_text, data.user_message, history_for_api)

    # Save the assistant's response to Supabase
    assistant_msg = save_message_to_supabase(session_id, "assistant", response)

    # Return the response to the client
    return {
        "session_id": session_id,
        "response": response,
        "user_message_id": user_msg.get("id"),
        "assistant_message_id": assistant_msg.get("id"),
        "is_new_session": is_new_session
    }
    
@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_sessions(username: str = Depends(get_current_user)):
    """Get all chat sessions for the current user."""
    sessions = get_user_chat_sessions(username)
    return sessions

@router.post("/sessions", response_model=Dict[str, Any])
async def create_session(data: CreateSessionRequest, username: str = Depends(get_current_user)):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    session = create_chat_session(
        session_id=session_id,
        username=username,
        title=data.title,
        document_id=data.document_id
    )
    return {"session_id": session_id, "session": session}

@router.put("/sessions/{session_id}", response_model=BaseResponse)
async def update_session(
    session_id: str, 
    data: UpdateSessionRequest, 
    username: str = Depends(get_current_user)
):
    """Update a chat session (title or end the session)."""
    # Check if the session exists and belongs to the user
    if not check_session_exists(session_id, username):
        raise HTTPException(status_code=403, detail="Chat session not found or access denied")
    
    update_data = {}
    if data.title:
        update_data["title"] = data.title
    
    if data.ended_at:
        update_data["ended_at"] = "now()"
    
    if update_data:
        try:
            supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()
            return BaseResponse(
                success=True,
                message="Chat session updated successfully",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update chat session: {e}")
    else:
        return BaseResponse(
            success=True,
            message="No changes to update",
        )

@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str, username: str = Depends(get_current_user)):
    """Get details of a specific chat session."""
    # Check if the session exists and belongs to the user
    if not check_session_exists(session_id, username):
        raise HTTPException(status_code=403, detail="Chat session not found or access denied")
    
    try:
        result = supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat session: {e}")

@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_session_history(
    session_id: str, 
    limit: int = 50, 
    offset: int = 0,
    username: str = Depends(get_current_user)
):
    """Get chat message history for a specific session."""
    # Check if the session exists and belongs to the user
    if not check_session_exists(session_id, username):
        raise HTTPException(status_code=403, detail="Chat session not found or access denied")
    
    messages = get_chat_history(session_id, limit, offset)
    return messages

@router.delete("/sessions/{session_id}", response_model=BaseResponse)
async def delete_session(session_id: str, username: str = Depends(get_current_user)):
    """Delete a chat session and all its messages."""
    # Check if the session exists and belongs to the user
    if not check_session_exists(session_id, username):
        raise HTTPException(status_code=403, detail="Chat session not found or access denied")
    
    try:
        # Delete the session (cascading delete will handle messages due to foreign key)
        supabase.table("chat_sessions").delete().eq("id", session_id).execute()
        
        return BaseResponse(
            success=True,
            message="Chat session deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {e}")
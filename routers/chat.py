import requests
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # Set your OpenRouter API key as an environment variable  # Replace with your site URL (optional)


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

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # Enforce a document size limit to avoid API issues
    if len(data.document_text) > 10000:  # Limit to 10,000 characters
        raise HTTPException(status_code=400, detail="Document too large. Please limit to 10,000 characters.")
    
    # Call OpenRouter to generate a response
    response = call_openrouter_model(data.document_text, data.user_message)

    # Return the response to the client
    return {"response": response}
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from db import supabase
import uuid

router = APIRouter()

# HuggingFace Inference API Configuration
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/google/t5-small"
HUGGINGFACE_API_KEY = "YOUR_HUGGINGFACE_API_KEY"  # Replace with your HuggingFace API key

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

def call_huggingface_model(prompt: str) -> str:
    """Call HuggingFace Inference API to generate a response."""
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"inputs": prompt}

    response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error from HuggingFace API: {response.text}")
    
    result = response.json()
    return result[0]["generated_text"]  # Adjust based on API response structure

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # Split document into manageable chunks
    splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=0)  # Larger chunks, no overlap
    chunks = splitter.split_text(data.document_text)

    # Use HuggingFace embeddings for creating the vector store
    embeddings = HuggingFaceEmbeddings()
    vectorstore = FAISS.from_texts(chunks, embeddings)
    retriever = vectorstore.as_retriever()

    # Limit the conversation memory to the last 5 exchanges to save memory
    memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)

    # Create the conversational chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=call_huggingface_model,  # Use the API-based model
        retriever=retriever,
        memory=memory
    )

    # Generate a response
    response = chain.run(data.user_message)

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
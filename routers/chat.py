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
import gc
import os
import psutil

router = APIRouter()

# HuggingFace Inference API Configuration
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/google/t5-small"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")  # Ensure this is set in Render's environment variables

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

def log_memory_usage(stage: str):
    """Logs the memory usage at a specific stage."""
    process = psutil.Process(os.getpid())
    print(f"{stage} - Memory usage: {process.memory_info().rss / 1024 ** 2:.2f} MB")

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
    # Enforce a document size limit
    if len(data.document_text) > 10000:  # Limit to 10,000 characters
        raise HTTPException(status_code=400, detail="Document too large. Please limit to 10,000 characters.")
    
    log_memory_usage("Start of chat endpoint")

    # Split document into manageable chunks
    splitter = CharacterTextSplitter(chunk_size=3000, chunk_overlap=0)  # Larger chunks, no overlap
    chunks = splitter.split_text(data.document_text)

    log_memory_usage("After splitting document")

    # Use HuggingFace embeddings for creating the vector store
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # Smaller embedding model
    vectorstore = FAISS.from_texts(chunks, embeddings)
    retriever = vectorstore.as_retriever()

    log_memory_usage("After creating vector store")

    # Limit the conversation memory to the last 3 exchanges to save memory
    memory = ConversationBufferWindowMemory(k=3, memory_key="chat_history", return_messages=True)

    # Create the conversational chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=call_huggingface_model,  # Use the API-based model
        retriever=retriever,
        memory=memory
    )

    # Generate a response
    response = chain.run(data.user_message)

    log_memory_usage("After generating response")

    # Cleanup FAISS and retriever objects to free memory
    del vectorstore
    del retriever
    gc.collect()

    log_memory_usage("After cleanup")

    # Save both messages to Supabase for chat history
    supabase.table("chat_messages").insert([
        {
            "id": str(uuid.uuid4()),
            "session_id": data.session_id,
            "role": "user",
            "content": data.user_message
        },
        {
            "id": str(uuid.uuid4()),  # Fixed missing closing parenthesis here
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
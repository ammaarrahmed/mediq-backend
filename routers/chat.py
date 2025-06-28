from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import HuggingFacePipeline
from langchain.text_splitter import CharacterTextSplitter
from transformers import pipeline
from db import supabase
import uuid

router = APIRouter()

# Initialize the HuggingFace model pipeline globally to avoid reloading on each request
hf_pipeline = pipeline("text2text-generation", model="t5-small", max_new_tokens=128)
global_llm = HuggingFacePipeline(pipeline=hf_pipeline)

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

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

    # Create the conversational chain with the lightweight model
    chain = ConversationalRetrievalChain.from_llm(
        llm=global_llm,  # Use the globally initialized lightweight model
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
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from db import supabase
import uuid

# Import a HuggingFace LLM wrapper, such as from langchain_community.llms if available
# You can pick any supported HuggingFace pipeline model, e.g., "google/flan-t5-base"
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline

router = APIRouter()

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # Split document into chunks
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(data.document_text)

    # Use HuggingFace embeddings (works without external server)
    embeddings = HuggingFaceEmbeddings()
    vectorstore = FAISS.from_texts(chunks, embeddings)
    retriever = vectorstore.as_retriever()

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    # Use HuggingFace for the LLM instead of Ollama
    # Choose a reasonable model for Q&A; here we use flan-t5-base as an example
    hf_pipeline = pipeline("text2text-generation", model="google/flan-t5-base", max_new_tokens=256)
    llm = HuggingFacePipeline(pipeline=hf_pipeline)

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory
    )

    response = chain.run(data.user_message)

    # Save both messages to Supabase
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
    result = supabase.table("chat_messages") \
        .select("role, content, created_at") \
        .eq("session_id", session_id) \
        .order("created_at", desc=False) \
        .execute()
    return result.data
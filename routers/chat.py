from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_community.llms import Ollama
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain.embeddings import OllamaEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from db import supabase
import uuid

router = APIRouter()

# Models
class ChatRequest(BaseModel):
    session_id: str
    document_text: str
    user_message: str

@router.post("/chat")
def chat_endpoint(data: ChatRequest):
    # 1. Embed document chunks
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(data.document_text)

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = FAISS.from_texts(chunks, embeddings)
    retriever = vectorstore.as_retriever()

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    llm = Ollama(model="llama3")

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

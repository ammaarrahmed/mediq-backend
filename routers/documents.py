from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from uuid import uuid4
from datetime import datetime
import os, shutil
from db import supabase
import pytesseract
from PIL import Image
from fastapi.responses import JSONResponse
from middleware.auth import get_current_user
from utils.medical_extractor import MedicalExtractor
import PyPDF2
from io import BytesIO

router = APIRouter()

UPLOAD_FOLDER = "uploads"

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), username: str = Depends(get_current_user)):
    try:
        # Ensure uploads/ folder exists
        UPLOAD_FOLDER = "uploads"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Save file locally
        ext = file.filename.split(".")[-1]
        filename = f"{uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # OCR extraction
        if ext.lower() in ["png", "jpg", "jpeg"]:
            img = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(img)
        elif ext.lower() == "pdf":
            # Read PDF
            try:
                with open(file_path, "rb") as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        text_parts.append(page.extract_text())
                    extracted_text = "\n".join(text_parts)
            except Exception as e:
                raise HTTPException(500, detail=f"Error processing PDF: {str(e)}")
        else:
            raise HTTPException(400, detail="Unsupported file type")
        
        # Extract medical information
        medical_info = MedicalExtractor.extract_all_medical_info(extracted_text)

        # Save to Supabase
        doc_data = {
            "user_id": username,
            "filename": filename,
            "text": extracted_text,
            "medical_data": medical_info,
            "processed_at": "now()",
            "file_type": ext.lower()
        }
        
        result = supabase.table("documents").insert(doc_data).execute()

        # Get the document ID from the result
        doc_id = result.data[0]["id"] if result.data else None
        
        return JSONResponse(content={
            "message": "Uploaded & processed",
            "document_id": doc_id,
            "filename": filename,
            "extracted_text": extracted_text[:500],
            "medical_info": medical_info
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/all")
def get_all_documents(username: str = Depends(get_current_user)):
    docs = supabase.table("documents").select("*").eq("user_id", username).execute().data
    return docs

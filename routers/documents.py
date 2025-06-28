from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from uuid import uuid4
from datetime import datetime
import os, shutil
from db import supabase
import pytesseract
from PIL import Image
from fastapi.responses import JSONResponse

router = APIRouter()

UPLOAD_FOLDER = "uploads"

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
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
            extracted_text = "PDF support pending"
        else:
            raise HTTPException(400, detail="Unsupported file type")

        # Save to Supabase
        supabase.table("documents").insert({
            "user_id": "test_user",
            "filename": filename,
            "text": extracted_text
        }).execute()

        return JSONResponse(content={
            "message": "Uploaded & processed",
            "filename": filename,
            "extracted_text": extracted_text[:500]
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/all")
def get_all_documents():
    docs = supabase.table("documents").select("*").execute().data
    return docs

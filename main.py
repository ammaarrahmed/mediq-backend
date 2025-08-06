import logging
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pytesseract

from config import settings
from routers import auth, documents, chat, profile, medical

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="MedIQ Backend", version="1.0.0")

# Configure Tesseract for deployment
if os.name == 'nt':  # Windows
    if settings.TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
# On Linux (Render), tesseract will be available in PATH

# Create upload directory
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/docs", tags=["Documents"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(profile.router, prefix="/profile", tags=["User Profiles"])
app.include_router(medical.router, prefix="/medical", tags=["Medical Analysis"])

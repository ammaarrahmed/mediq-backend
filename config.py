import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".pdf"}
    UPLOAD_FOLDER: str = "uploads"
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://mediq-frontend-2lm7.onrender.com",
        "https://mediq-frontend-2lm7.onrender.com/",
        # Add your production domain here later
    ]
    
    # Tesseract - this fixes your deployment issue!
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "tesseract")
    
    def validate(self):
        """Validate required environment variables"""
        required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "SECRET_KEY"]
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

settings = Settings()
settings.validate()
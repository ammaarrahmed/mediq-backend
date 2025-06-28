import logging
from supabase import create_client, Client
from config import settings
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Singleton pattern for Supabase client"""
        if cls._instance is None:
            try:
                cls._instance = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("✅ Connected to Supabase successfully")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Supabase: {e}")
                raise
        return cls._instance

# Global instance
supabase = DatabaseManager.get_client()
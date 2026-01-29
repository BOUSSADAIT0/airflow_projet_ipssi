# app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Tesseract
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "/usr/local/bin/tesseract")
    
    # Application
    APP_NAME: str = "OCR Intelligent API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Fichiers
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
    
    # Redis (optionnel)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    class Config:
        env_file = ".env"

# Créez une instance de settings
settings = Settings()

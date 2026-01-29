import os
import shutil
import tempfile
from typing import Optional
from fastapi import UploadFile, HTTPException
from app.config import settings

def ensure_directories():
    """Crée les répertoires nécessaires s'ils n'existent pas"""
    directories = [
        settings.UPLOAD_DIR,
        settings.STATIC_DIR,
        os.path.join(settings.STATIC_DIR, "previews"),
        os.path.join(settings.UPLOAD_DIR, "documents"),
        os.path.join(settings.UPLOAD_DIR, "exports"),
        os.path.join(settings.UPLOAD_DIR, "temp")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def validate_file_extension(filename: str) -> bool:
    """Valide l'extension du fichier"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format de fichier non supporté. Formats autorisés: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    return True

async def save_upload_file(upload_file: UploadFile, user_id: Optional[int] = None) -> str:
    """Sauvegarde un fichier uploadé"""
    validate_file_extension(upload_file.filename)
    
    # Création du répertoire utilisateur si besoin
    if user_id:
        user_dir = os.path.join(settings.UPLOAD_DIR, "documents", str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        filename = f"{user_id}_{upload_file.filename}"
        file_path = os.path.join(user_dir, filename)
    else:
        file_path = os.path.join(settings.UPLOAD_DIR, "temp", upload_file.filename)
    
    # Sauvegarde du fichier
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path

def save_temp_file(file_bytes: bytes, filename: str) -> str:
    """Sauvegarde un fichier temporaire"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"ocr_temp_{filename}")
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
    
    return temp_path

def cleanup_temp_file(file_path: str):
    """Supprime un fichier temporaire"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

def get_file_size(file_path: str) -> int:
    """Récupère la taille d'un fichier en bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def get_file_hash(file_path: str) -> str:
    """Calcule le hash d'un fichier"""
    import hashlib
    
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    return hash_md5.hexdigest()

def safe_filename(filename: str) -> str:
    """Nettoie un nom de fichier pour le rendre sûr"""
    import re
    
    # Suppression des caractères dangereux
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    filename = filename.strip()
    
    # Limitation de la longueur
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename
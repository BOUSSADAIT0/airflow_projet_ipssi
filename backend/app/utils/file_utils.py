import os
import shutil
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.config import settings

class FileUtils:
    @staticmethod
    async def save_upload_file(upload_file: UploadFile, user_id: Optional[int] = None) -> Tuple[str, str]:
        """
        Sauvegarde un fichier uploadé et retourne le chemin
        """
        try:
            # Valider l'extension
            filename = upload_file.filename
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in settings.ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Format de fichier non supporté. Formats autorisés: {', '.join(settings.ALLOWED_EXTENSIONS)}"
                )
            
            # Créer le répertoire si nécessaire
            upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id) if user_id else "anonymous")
            os.makedirs(upload_dir, exist_ok=True)
            
            # Générer un nom de fichier unique
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Sauvegarder le fichier
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            return file_path, unique_filename
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la sauvegarde du fichier: {str(e)}"
            )
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Récupère les informations d'un fichier
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
            
            stat = os.stat(file_path)
            
            return {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': os.path.splitext(file_path)[1].lower()
            }
            
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération des infos du fichier: {str(e)}")
    
    @staticmethod
    def create_preview(image_path: str, output_dir: str, size: Tuple[int, int] = (800, 800)) -> Optional[str]:
        """
        Crée un aperçu d'une image
        """
        try:
            from PIL import Image
            
            # Charger l'image
            img = Image.open(image_path)
            
            # Créer un aperçu
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Sauvegarder l'aperçu
            preview_filename = f"preview_{os.path.basename(image_path)}.png"
            preview_path = os.path.join(output_dir, preview_filename)
            
            # Convertir en PNG si nécessaire
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.save(preview_path, 'PNG', optimize=True)
            
            return preview_path
            
        except Exception as e:
            print(f"Erreur création preview: {str(e)}")
            return None
    
    @staticmethod
    def cleanup_old_files(directory: str, max_age_days: int = 7):
        """
        Nettoie les anciens fichiers
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        print(f"Fichier supprimé: {file_path}")
                        
        except Exception as e:
            print(f"Erreur nettoyage fichiers: {str(e)}")
    
    @staticmethod
    def generate_download_url(file_path: str, base_url: str) -> str:
        """
        Génère une URL de téléchargement
        """
        relative_path = os.path.relpath(file_path, settings.UPLOAD_DIR)
        return f"{base_url}/download/{relative_path}"
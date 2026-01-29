import re
import mimetypes
from typing import List, Optional
from datetime import datetime
import magic
from fastapi import HTTPException

class DocumentValidator:
    """Validateur de documents"""
    
    ALLOWED_MIME_TYPES = {
        'application/pdf': '.pdf',
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': '.png',
        'image/tiff': ['.tiff', '.tif'],
        'image/bmp': '.bmp',
        'image/gif': '.gif'
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def validate_file_size(cls, file_size: int) -> bool:
        """Valide la taille du fichier"""
        if file_size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {cls.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        return True
    
    @classmethod
    def validate_file_type(cls, file_content: bytes, filename: str) -> bool:
        """Valide le type de fichier"""
        # Détection du type MIME
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(file_content[:2048])  # Lire seulement les premiers bytes
        
        # Vérification de l'extension
        extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Vérification du type MIME autorisé
        if mime_type not in cls.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {mime_type}"
            )
        
        # Vérification de la correspondance extension/MIME
        allowed_extensions = cls.ALLOWED_MIME_TYPES[mime_type]
        if isinstance(allowed_extensions, list):
            if extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"File extension {extension} does not match MIME type {mime_type}"
                )
        elif extension != allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File extension {extension} does not match MIME type {mime_type}"
            )
        
        return True
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Valide le nom de fichier"""
        # Vérification de la longueur
        if len(filename) > 255:
            raise HTTPException(
                status_code=400,
                detail="Filename too long"
            )
        
        # Vérification des caractères interdits
        forbidden_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in forbidden_chars:
            if char in filename:
                raise HTTPException(
                    status_code=400,
                    detail=f"Filename contains forbidden character: {char}"
                )
        
        return True

class DataValidator:
    """Validateur de données"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valide une adresse email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Valide un numéro de téléphone"""
        # Suppression des espaces et caractères spéciaux
        cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
        
        # Formats acceptés : +33123456789 ou 0123456789
        pattern = r'^(\+33[1-9]|0[1-9])\d{8}$'
        return bool(re.match(pattern, cleaned))
    
    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """Valide une date"""
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_amount(amount_str: str) -> Optional[float]:
        """Valide un montant"""
        try:
            # Nettoyage du montant
            cleaned = re.sub(r'[^\d,\.]', '', amount_str)
            cleaned = cleaned.replace(',', '.')
            
            # Conversion en float
            amount = float(cleaned)
            
            if amount < 0:
                return None
            
            return amount
        except ValueError:
            return None
    
    @staticmethod
    def validate_percentage(percentage_str: str) -> Optional[float]:
        """Valide un pourcentage"""
        try:
            # Extraction du nombre
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', percentage_str)
            if not match:
                return None
            
            percentage = float(match.group(1))
            
            if 0 <= percentage <= 100:
                return percentage
            
            return None
        except ValueError:
            return None

class OCRResultValidator:
    """Validateur de résultats OCR"""
    
    @staticmethod
    def validate_confidence(confidence: float) -> bool:
        """Valide un score de confiance"""
        return 0.0 <= confidence <= 1.0
    
    @staticmethod
    def validate_extracted_data(data: dict) -> List[str]:
        """Valide les données extraites"""
        errors = []
        
        # Vérification de la structure de base
        required_keys = ['document_type', 'fields', 'extraction_date']
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required key: {key}")
        
        # Vérification des champs extraits
        if 'fields' in data:
            fields = data['fields']
            if not isinstance(fields, dict):
                errors.append("Fields should be a dictionary")
            else:
                for field_name, field_values in fields.items():
                    if not isinstance(field_values, list):
                        errors.append(f"Field values for {field_name} should be a list")
        
        return errors
    
    @staticmethod
    def validate_zones(zones: list) -> List[str]:
        """Valide les zones détectées"""
        errors = []
        
        for zone in zones:
            if not isinstance(zone, dict):
                errors.append("Zone should be a dictionary")
                continue
            
            required_keys = ['x', 'y', 'width', 'height']
            for key in required_keys:
                if key not in zone:
                    errors.append(f"Zone missing required key: {key}")
                elif not isinstance(zone[key], (int, float)):
                    errors.append(f"Zone {key} should be a number")
            
            # Vérification des valeurs positives
            if 'width' in zone and zone['width'] <= 0:
                errors.append("Zone width should be positive")
            if 'height' in zone and zone['height'] <= 0:
                errors.append("Zone height should be positive")
        
        return errors

class UserInputValidator:
    """Validateur d'entrées utilisateur"""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Nettoie un texte"""
        import html
        
        # Échappement HTML
        sanitized = html.escape(text)
        
        # Limitation de longueur
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_username(username: str) -> List[str]:
        """Valide un nom d'utilisateur"""
        errors = []
        
        # Longueur
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        if len(username) > 50:
            errors.append("Username must be at most 50 characters long")
        
        # Caractères autorisés
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            errors.append("Username can only contain letters, numbers, dots, dashes and underscores")
        
        # Mots interdits
        forbidden_words = ['admin', 'root', 'system', 'test']
        if username.lower() in forbidden_words:
            errors.append("This username is not allowed")
        
        return errors
    
    @staticmethod
    def validate_password(password: str) -> List[str]:
        """Valide un mot de passe"""
        errors = []
        
        # Longueur
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if len(password) > 128:
            errors.append("Password must be at most 128 characters long")
        
        # Complexité
        if not any(char.isdigit() for char in password):
            errors.append("Password must contain at least one digit")
        
        if not any(char.isupper() for char in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(char.islower() for char in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
            errors.append("Password must contain at least one special character")
        
        return errors
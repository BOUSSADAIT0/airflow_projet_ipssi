import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Vérifie un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Récupère l'utilisateur courant depuis le token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"username": username}

def generate_api_key() -> str:
    """Génère une clé API sécurisée"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash un mot de passe"""
    import hashlib
    import bcrypt
    
    # Utilisation de bcrypt pour un hash sécurisé
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe"""
    import bcrypt
    
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def validate_password_strength(password: str) -> dict:
    """Valide la force d'un mot de passe"""
    errors = []
    
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères")
    
    if not any(char.isdigit() for char in password):
        errors.append("Le mot de passe doit contenir au moins un chiffre")
    
    if not any(char.isupper() for char in password):
        errors.append("Le mot de passe doit contenir au moins une majuscule")
    
    if not any(char.islower() for char in password):
        errors.append("Le mot de passe doit contenir au moins une minuscule")
    
    if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
        errors.append("Le mot de passe doit contenir au moins un caractère spécial")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def sanitize_input(input_string: str) -> str:
    """Nettoie une chaîne de caractères pour prévenir les injections"""
    import html
    
    # Échappement des caractères HTML
    sanitized = html.escape(input_string)
    
    # Suppression des caractères de contrôle
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    return sanitized

def generate_csrf_token() -> str:
    """Génère un token CSRF"""
    return secrets.token_hex(32)
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt  # Utiliser PyJWT pour la cohérence
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt

from app.config import settings
from app.database.session import get_db
from app.models.user import User

security = HTTPBearer()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crée un token JWT d'accès"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any], expires_delta: timedelta = timedelta(days=7)) -> str:
    """Crée un token JWT de rafraîchissement"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Vérifie un token JWT"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "type", "sub"]}
        )
        
        # Vérifier le type de token
        if payload.get("type") != token_type:
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_password_hash(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds pour la sécurité
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe hashé"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur courant depuis le token"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide: sujet manquant",
        )
    
    # Récupérer l'utilisateur depuis la base de données
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur désactivé",
        )
    
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Vérifie que l'utilisateur courant est un superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissions insuffisantes"
        )
    return current_user

def generate_api_key() -> str:
    """Génère une clé API sécurisée"""
    return secrets.token_urlsafe(32)

def generate_csrf_token() -> str:
    """Génère un token CSRF"""
    return secrets.token_hex(32)

def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Nettoie une chaîne de caractères pour prévenir les injections"""
    import html
    
    # Échappement HTML
    sanitized = html.escape(input_string)
    
    # Suppression des caractères de contrôle
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    # Limitation de longueur
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_token_expiration(expiration_timestamp: int) -> bool:
    """Valide l'expiration d'un token"""
    expiration_time = datetime.fromtimestamp(expiration_timestamp)
    return expiration_time > datetime.utcnow()

def rotate_secret_key() -> str:
    """Génère une nouvelle clé secrète (pour rotation)"""
    return secrets.token_urlsafe(64)
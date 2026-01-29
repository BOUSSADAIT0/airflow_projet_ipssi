from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db, SessionLocal, init_db
from app.models.user import User as UserModel

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Modèles Pydantic
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None
    password: str

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.email == email).first()


def init_default_users():
    """
    Crée les utilisateurs par défaut dans la base de données s'ils n'existent pas
    et supprime l'ancien utilisateur 'demo' si présent.
    """
    # S'assurer que les tables existent
    init_db()

    db = SessionLocal()
    try:
        # Supprimer l'ancien utilisateur de démo s'il existe encore
        demo = db.query(UserModel).filter(UserModel.username == "demo").first()
        if demo:
            db.delete(demo)
            db.commit()

        default_users = [
            {
                "email": "admin@ocri.com",
                "username": "admin",
                "full_name": "Administrateur OCR Intelligent",
                "password": "Admin123!",
                "is_superuser": True,
            },
            {
                "email": "user@ocri.com",
                "username": "user",
                "full_name": "Utilisateur OCR",
                "password": "User123!",
                "is_superuser": False,
            },
            {
                "email": "test@ocri.com",
                "username": "testeur",
                "full_name": "Utilisateur de Test OCR",
                "password": "Test123!",
                "is_superuser": False,
            },
        ]

        for u in default_users:
            existing = db.query(UserModel).filter(
                (UserModel.username == u["username"]) | (UserModel.email == u["email"])
            ).first()
            if not existing:
                user = UserModel(
                    email=u["email"],
                    username=u["username"],
                    full_name=u["full_name"],
                    hashed_password=get_password_hash(u["password"]),
                    is_active=True,
                    is_superuser=u["is_superuser"],
                )
                db.add(user)
        db.commit()
    finally:
        db.close()


# Initialisation des utilisateurs par défaut au chargement du module
init_default_users()

@router.post("/register", response_model=User)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Enregistre un nouvel utilisateur"""
    # Vérifier unicité username / email
    if get_user_by_username(db, user_data.username):
        # 409 Conflict pour correspondre au frontend
        raise HTTPException(status_code=409, detail="Nom d'utilisateur déjà utilisé")

    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    db_user = UserModel(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name or "",
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return User.model_validate(db_user)

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authentifie un utilisateur"""
    user = get_user_by_username(db, user_data.username)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=User)
async def get_current_user(token: str, db: Session = Depends(get_db)):
    """Récupère les informations de l'utilisateur connecté"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(status_code=401, detail="Token invalide")

        user = get_user_by_username(db, username)
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")

        return User.model_validate(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.post("/refresh")
async def refresh_token(token: str, db: Session = Depends(get_db)):
    """Rafraîchit le token d'authentification"""
    try:
        # Accepter les tokens expirés pour le rafraîchissement
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )

        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token invalide")

        user = get_user_by_username(db, username)
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")

        new_token = create_access_token(data={"sub": username})
        return Token(access_token=new_token, token_type="bearer")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

@router.post("/logout")
async def logout():
    """Déconnecte l'utilisateur"""
    return {"success": True, "message": "Déconnexion réussie"}
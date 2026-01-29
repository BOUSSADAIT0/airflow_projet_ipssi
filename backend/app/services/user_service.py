from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.api.auth import get_password_hash

class UserService:
    """Service de gestion des utilisateurs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Récupère un utilisateur par son nom d'utilisateur"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Récupère tous les utilisateurs"""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Crée un nouvel utilisateur"""
        hashed_password = get_password_hash(user_data.password)
        
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def update_user(self, user_id: int, user_update: Dict[str, Any]) -> User:
        """Met à jour un utilisateur"""
        db_user = self.get_user_by_id(user_id)
        
        if not db_user:
            raise ValueError("User not found")
        
        update_data = user_update.dict(exclude_unset=True) if hasattr(user_update, 'dict') else user_update
        
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            if hasattr(db_user, field):
                setattr(db_user, field, value)
        
        db_user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def delete_user(self, user_id: int) -> bool:
        """Supprime un utilisateur"""
        db_user = self.get_user_by_id(user_id)
        
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        
        return True
    
    def update_last_login(self, user_id: int):
        """Met à jour la date de dernière connexion"""
        db_user = self.get_user_by_id(user_id)
        
        if db_user:
            db_user.last_login = datetime.utcnow()
            self.db.commit()
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Récupère les statistiques d'un utilisateur"""
        from app.models.document import Document, ExtractionResult
        
        # Nombre de documents
        total_docs = self.db.query(func.count(Document.id))\
                           .filter(Document.user_id == user_id)\
                           .scalar()
        
        # Nombre de documents traités
        processed_docs = self.db.query(func.count(Document.id))\
                               .filter(Document.user_id == user_id, Document.status == "completed")\
                               .scalar()
        
        # Nombre d'extractions réussies
        successful_extractions = self.db.query(func.count(ExtractionResult.id))\
                                       .filter(ExtractionResult.user_id == user_id)\
                                       .scalar()
        
        # Moyenne de confiance
        avg_confidence = self.db.query(func.avg(ExtractionResult.confidence_score))\
                               .filter(ExtractionResult.user_id == user_id)\
                               .scalar()
        
        # Dernier traitement
        last_processing = self.db.query(ExtractionResult.extraction_date)\
                                .filter(ExtractionResult.user_id == user_id)\
                                .order_by(ExtractionResult.extraction_date.desc())\
                                .first()
        
        return {
            "total_documents": total_docs or 0,
            "processed_documents": processed_docs or 0,
            "successful_extractions": successful_extractions or 0,
            "average_confidence": round(avg_confidence or 0, 2),
            "last_processing": last_processing[0] if last_processing else None
        }
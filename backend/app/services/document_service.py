import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.document import Document, ExtractionResult
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.utils.file_handler import save_temp_file, cleanup_temp_file, get_file_size
from app.config import settings

class DocumentService:
    """Service de gestion des documents"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_document(
        self, 
        filename: str, 
        file_bytes: bytes, 
        user_id: int
    ) -> Document:
        """Crée un nouveau document en base de données"""
        try:
            # Génération d'un nom de fichier unique
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Sauvegarde du fichier
            upload_dir = os.path.join(settings.UPLOAD_DIR, "documents", str(user_id))
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, unique_filename)
            
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            
            # Création de l'entrée en base
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                file_size=get_file_size(file_path),
                file_type=os.path.splitext(filename)[1][1:].lower(),
                upload_date=datetime.utcnow(),
                status="pending",
                user_id=user_id
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            return document
            
        except Exception as e:
            self.db.rollback()
            raise
    
    async def update_document_status(
        self, 
        document_id: int, 
        status: str, 
        error_message: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Document:
        """Met à jour le statut d'un document"""
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError("Document not found")
        
        document.status = status
        if error_message:
            document.error_message = error_message
        if document_type:
            document.document_type = document_type
        
        if status == "completed":
            document.processed_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(document)
        
        return document
    
    async def save_extraction_result(
        self, 
        document_id: int, 
        result: Dict[str, Any], 
        user_id: int
    ) -> ExtractionResult:
        """Sauvegarde les résultats d'extraction"""
        try:
            # Sauvegarde des données extraites dans un fichier JSON
            export_dir = os.path.join(settings.UPLOAD_DIR, "exports", str(user_id))
            os.makedirs(export_dir, exist_ok=True)
            
            json_filename = f"{result['process_id']}.json"
            json_path = os.path.join(export_dir, json_filename)
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Création de l'entrée en base
            extraction_result = ExtractionResult(
                process_id=result["process_id"],
                document_id=document_id,
                user_id=user_id,
                extracted_data=result["extracted_data"],
                raw_text=result.get("raw_text", ""),
                confidence_score=result["confidence"],
                zones=result.get("zones", []),
                preview_path=result.get("preview_url", ""),
                extraction_date=datetime.utcnow(),
                processing_time=result.get("processing_time", 0),
                json_path=json_path
            )
            
            self.db.add(extraction_result)
            self.db.commit()
            self.db.refresh(extraction_result)
            
            # Mise à jour du document
            await self.update_document_status(
                document_id,
                "completed",
                document_type=result["document_type"]
            )
            
            return extraction_result
            
        except Exception as e:
            self.db.rollback()
            raise
    
    async def get_user_documents(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Document]:
        """Récupère les documents d'un utilisateur"""
        query = self.db.query(Document).filter(Document.user_id == user_id)
        
        if status:
            query = query.filter(Document.status == status)
        
        documents = query.order_by(desc(Document.upload_date))\
                        .offset(skip)\
                        .limit(limit)\
                        .all()
        
        return documents
    
    async def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Récupère un document par son ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    async def get_document_by_filename(self, filename: str, user_id: int) -> Optional[Document]:
        """Récupère un document par son nom de fichier"""
        return self.db.query(Document)\
                     .filter(Document.original_filename == filename, Document.user_id == user_id)\
                     .first()
    
    async def delete_document(self, document_id: int) -> bool:
        """Supprime un document"""
        document = await self.get_document_by_id(document_id)
        
        if not document:
            return False
        
        try:
            # Suppression du fichier physique
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # Suppression des résultats associés
            results = self.db.query(ExtractionResult)\
                           .filter(ExtractionResult.document_id == document_id)\
                           .all()
            
            for result in results:
                # Suppression des fichiers d'export
                for path_field in ['json_path', 'csv_path', 'excel_path']:
                    path = getattr(result, path_field)
                    if path and os.path.exists(path):
                        os.remove(path)
                
                # Suppression de l'entrée en base
                self.db.delete(result)
            
            # Suppression du document
            self.db.delete(document)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise
    
    async def get_user_results(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        document_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ExtractionResult]:
        """Récupère les résultats d'un utilisateur avec filtres"""
        query = self.db.query(ExtractionResult)\
                      .filter(ExtractionResult.user_id == user_id)\
                      .join(Document)\
                      .filter(Document.status == "completed")
        
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        if min_confidence:
            query = query.filter(ExtractionResult.confidence_score >= min_confidence)
        
        if start_date:
            query = query.filter(ExtractionResult.extraction_date >= start_date)
        
        if end_date:
            query = query.filter(ExtractionResult.extraction_date <= end_date)
        
        results = query.order_by(desc(ExtractionResult.extraction_date))\
                      .offset(skip)\
                      .limit(limit)\
                      .all()
        
        return results
    
    async def get_result_by_process_id(self, process_id: str) -> Optional[ExtractionResult]:
        """Récupère un résultat par son process ID"""
        return self.db.query(ExtractionResult)\
                     .filter(ExtractionResult.process_id == process_id)\
                     .first()
    
    async def save_export(
        self,
        result_id: int,
        export_data: Dict[str, Any],
        format: str
    ) -> str:
        """Sauvegarde un fichier exporté"""
        result = self.db.query(ExtractionResult)\
                       .filter(ExtractionResult.id == result_id)\
                       .first()
        
        if not result:
            raise ValueError("Result not found")
        
        # Création du répertoire d'export
        export_dir = os.path.join(settings.UPLOAD_DIR, "exports", str(result.user_id))
        os.makedirs(export_dir, exist_ok=True)
        
        # Chemin du fichier
        export_path = os.path.join(export_dir, export_data["filename"])
        
        # Sauvegarde du fichier
        if isinstance(export_data["data"], str):
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(export_data["data"])
        else:
            with open(export_path, "wb") as f:
                f.write(export_data["data"])
        
        # Mise à jour du chemin dans la base
        if format == "csv":
            result.csv_path = export_path
        elif format == "excel":
            result.excel_path = export_path
        
        self.db.commit()
        
        return export_path
    
    async def get_document_statistics(self, user_id: int) -> Dict[str, Any]:
        """Récupère les statistiques des documents d'un utilisateur"""
        # Nombre total de documents
        total_docs = self.db.query(Document)\
                           .filter(Document.user_id == user_id)\
                           .count()
        
        # Documents par statut
        status_counts = {}
        for status in ["pending", "processing", "completed", "failed"]:
            count = self.db.query(Document)\
                          .filter(Document.user_id == user_id, Document.status == status)\
                          .count()
            status_counts[status] = count
        
        # Documents par type
        type_counts = {}
        doc_types = self.db.query(Document.document_type)\
                          .filter(Document.user_id == user_id, Document.document_type.isnot(None))\
                          .distinct()\
                          .all()
        
        for doc_type in doc_types:
            if doc_type[0]:
                count = self.db.query(Document)\
                              .filter(Document.user_id == user_id, Document.document_type == doc_type[0])\
                              .count()
                type_counts[doc_type[0]] = count
        
        # Moyenne de confiance
        avg_confidence = self.db.query(func.avg(ExtractionResult.confidence_score))\
                               .filter(ExtractionResult.user_id == user_id)\
                               .scalar()
        
        return {
            "total_documents": total_docs,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "average_confidence": avg_confidence or 0
        }
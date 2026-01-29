from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime

from app.config import settings
from app.schemas.document import Document, DocumentCreate, DocumentUpdate
from app.schemas.ocr import OCRRequest, OCRResponse, BatchOCRRequest, BatchOCRResponse
from app.services.document_service import DocumentService
from app.services.ocr_service import OCRService
from app.utils.file_handler import save_upload_file, validate_file_extension
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/upload", response_model=OCRResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    language: str = Form("fra+eng"),
    export_format: str = Form("json"),
    current_user: User = Depends(get_current_user)
):
    """Télécharge et traite un document"""
    try:
        # Validation du fichier
        validate_file_extension(file.filename)
        
        # Sauvegarde temporaire du fichier
        file_bytes = await file.read()
        
        # Traitement OCR
        ocr_service = OCRService()
        result = ocr_service.process_single_file(
            file_bytes=file_bytes,
            filename=file.filename,
            language=language,
            user_id=current_user.id if current_user else None
        )
        
        # Sauvegarde en base de données
        if current_user:
            document_service = DocumentService()
            document = await document_service.create_document(
                filename=file.filename,
                file_bytes=file_bytes,
                user_id=current_user.id
            )
            
            await document_service.save_extraction_result(
                document_id=document.id,
                result=result,
                user_id=current_user.id
            )
        
        # Génération des URLs de téléchargement
        download_urls = {}
        if export_format == "json":
            download_urls["json"] = f"/api/v1/results/{result['process_id']}/export/json"
        elif export_format == "csv":
            download_urls["csv"] = f"/api/v1/results/{result['process_id']}/export/csv"
        
        response = OCRResponse(
            success=True,
            process_id=result["process_id"],
            filename=result["filename"],
            document_type=result["document_type"],
            confidence=result["confidence"],
            extracted_data=result["extracted_data"],
            processing_time=result.get("processing_time", 0),
            preview_url=result.get("preview_url"),
            download_urls=download_urls
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

@router.post("/upload/batch", response_model=BatchOCRResponse)
async def upload_and_process_batch(
    files: List[UploadFile] = File(...),
    language: str = Form("fra+eng"),
    export_format: str = Form("json"),
    current_user: User = Depends(get_current_user)
):
    """Télécharge et traite plusieurs documents"""
    try:
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 fichiers autorisés")
        
        ocr_service = OCRService()
        results = []
        successful = 0
        failed = 0
        
        for file in files:
            try:
                validate_file_extension(file.filename)
                file_bytes = await file.read()
                
                result = ocr_service.process_single_file(
                    file_bytes=file_bytes,
                    filename=file.filename,
                    language=language,
                    user_id=current_user.id if current_user else None
                )
                
                # Sauvegarde en base
                if current_user:
                    document_service = DocumentService()
                    document = await document_service.create_document(
                        filename=file.filename,
                        file_bytes=file_bytes,
                        user_id=current_user.id
                    )
                    
                    await document_service.save_extraction_result(
                        document_id=document.id,
                        result=result,
                        user_id=current_user.id
                    )
                
                results.append(OCRResponse(
                    success=True,
                    process_id=result["process_id"],
                    filename=result["filename"],
                    document_type=result["document_type"],
                    confidence=result["confidence"],
                    extracted_data=result["extracted_data"],
                    processing_time=result.get("processing_time", 0),
                    preview_url=result.get("preview_url")
                ))
                successful += 1
                
            except Exception as e:
                failed += 1
                results.append(OCRResponse(
                    success=False,
                    process_id=str(uuid.uuid4()),
                    filename=file.filename,
                    document_type="error",
                    confidence=0.0,
                    extracted_data={"error": str(e)},
                    processing_time=0
                ))
        
        response = BatchOCRResponse(
            success=True,
            total_files=len(files),
            successful_files=successful,
            failed_files=failed,
            results=results,
            batch_id=str(uuid.uuid4())
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement batch: {str(e)}")

@router.get("/documents", response_model=List[Document])
async def get_user_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Récupère les documents de l'utilisateur"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    document_service = DocumentService()
    documents = await document_service.get_user_documents(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return documents

@router.get("/documents/{document_id}", response_model=Document)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user)
):
    """Récupère un document spécifique"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    document_service = DocumentService()
    document = await document_service.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    if document.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return document

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user)
):
    """Supprime un document"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    document_service = DocumentService()
    document = await document_service.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    
    if document.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    success = await document_service.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")
    
    return {"success": True, "message": "Document supprimé"}
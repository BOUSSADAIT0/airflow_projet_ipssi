from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, List
import uuid
import json
from datetime import datetime

from app.schemas.ocr import OCRRequest, OCRResponse, BatchOCRRequest, BatchOCRResponse
from app.services.ocr_service import OCRService
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/process", response_model=OCRResponse)
async def process_document(
    request: OCRRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Traite un document à partir de contenu base64"""
    try:
        import base64
        
        # Décodage base64
        file_bytes = base64.b64decode(request.file_content)
        
        ocr_service = OCRService()
        
        # Traitement en arrière-plan
        result = await ocr_service.process_async(
            file_bytes=file_bytes,
            filename=request.filename,
            language=request.language,
            user_id=current_user.id if current_user else None,
            background_tasks=background_tasks
        )
        
        return OCRResponse(
            success=True,
            process_id=result["process_id"],
            filename=result["filename"],
            document_type=result["document_type"],
            confidence=result["confidence"],
            extracted_data=result["extracted_data"],
            processing_time=result.get("processing_time", 0),
            preview_url=result.get("preview_url")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

@router.post("/process/batch", response_model=BatchOCRResponse)
async def process_batch(
    request: BatchOCRRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Traite plusieurs documents en batch"""
    try:
        import base64
        
        ocr_service = OCRService()
        results = []
        successful = 0
        failed = 0
        
        for file_request in request.files:
            try:
                file_bytes = base64.b64decode(file_request.file_content)
                
                result = await ocr_service.process_async(
                    file_bytes=file_bytes,
                    filename=file_request.filename,
                    language=file_request.language,
                    user_id=request.user_id or (current_user.id if current_user else None),
                    background_tasks=background_tasks
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
                    filename=file_request.filename,
                    document_type="error",
                    confidence=0.0,
                    extracted_data={"error": str(e)},
                    processing_time=0
                ))
        
        response = BatchOCRResponse(
            success=True,
            total_files=len(request.files),
            successful_files=successful,
            failed_files=failed,
            results=results,
            batch_id=str(uuid.uuid4())
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traitement batch: {str(e)}")

@router.get("/status/{process_id}")
async def get_processing_status(
    process_id: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère le statut d'un traitement"""
    try:
        ocr_service = OCRService()
        status = await ocr_service.get_processing_status(process_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Traitement non trouvé")
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_processing_statistics(
    current_user: User = Depends(get_current_user)
):
    """Récupère les statistiques de traitement"""
    try:
        ocr_service = OCRService()
        stats = ocr_service.get_statistics()
        
        return {
            "total_documents_processed": stats["documents_processed"],
            "total_pages_processed": stats["total_pages"],
            "average_confidence": stats["average_confidence"],
            "user_specific": current_user.id if current_user else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
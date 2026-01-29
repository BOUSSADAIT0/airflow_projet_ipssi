from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import uuid
import os
from datetime import datetime

from app.utils.ocr_processor import OCRProcessor
from app.config import settings

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# Initialiser le processeur OCR
ocr_processor = OCRProcessor(
    tesseract_path=settings.TESSERACT_PATH,
    default_language=settings.DEFAULT_LANGUAGE
)

@router.post("/extract")
async def extract_text(
    file: UploadFile = File(...),
    language: str = Form("fra+eng")
):
    """Extrait le texte d'un document"""
    try:
        # Vérifier le type de fichier
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Lire le fichier
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Fichier vide")
        
        # Traitement OCR
        result = ocr_processor.process_file(content, file.filename, language)
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur OCR: {result.get('error', 'Erreur inconnue')}"
            )
        
        # Générer un ID de processus
        process_id = str(uuid.uuid4())
        
        return {
            "success": True,
            "process_id": process_id,
            "filename": file.filename,
            "document_type": result['structured_data'].get('document_type', 'unknown'),
            "confidence": result['average_confidence'],
            "text": result['text'],
            "structured_data": result['structured_data'],
            "pages": len(result['pages']),
            "processing_time": 0,  # À améliorer avec un timer
            "extracted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/batch-extract")
async def batch_extract(
    files: list[UploadFile] = File(...),
    language: str = Form("fra+eng")
):
    """Extrait le texte de plusieurs documents"""
    try:
        results = []
        
        for file in files:
            try:
                content = await file.read()
                result = ocr_processor.process_file(content, file.filename, language)
                
                results.append({
                    "filename": file.filename,
                    "success": result['success'],
                    "text": result['text'] if result['success'] else "",
                    "error": result.get('error') if not result['success'] else None,
                    "pages": result['total_pages'],
                    "confidence": result['average_confidence']
                })
                
                # Réinitialiser le pointeur du fichier pour le prochain traitement
                await file.seek(0)
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e),
                    "text": "",
                    "pages": 0,
                    "confidence": 0
                })
        
        return {
            "success": True,
            "total_files": len(files),
            "processed_files": len([r for r in results if r['success']]),
            "failed_files": len([r for r in results if not r['success']]),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
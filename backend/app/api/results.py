from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import os
import json

from app.schemas.result import ExtractionResult, ExportResponse
from app.config import settings
from app.database.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/results", tags=["Results"])

@router.get("/{process_id}", response_model=ExtractionResult)
async def get_result(
    process_id: str,
    db: Session = Depends(get_db)
):
    """
    Récupère les résultats d'un traitement
    """
    try:
        # Récupérer depuis la base de données
        # result = db.query(...).filter(...).first()
        
        # Pour l'exemple, simuler des données
        if not process_id:
            raise HTTPException(status_code=404, detail="Processus non trouvé")
        
        # Simuler des données de résultat
        result_data = {
            "id": 1,
            "process_id": process_id,
            "document_id": 1,
            "user_id": 1,
            "extracted_data": {
                "document_type": "invoice",
                "invoice_number": "FAC-2024-001",
                "date": "2024-01-15",
                "total_amount": "1500.00",
                "client_name": "Entreprise ABC"
            },
            "raw_text": "Facture n° FAC-2024-001\nDate: 15/01/2024\nClient: Entreprise ABC\nTotal: 1500.00 €",
            "confidence_score": 0.92,
            "zones": [
                {
                    "text": "Facture",
                    "x": 100,
                    "y": 50,
                    "width": 200,
                    "height": 30,
                    "type": "header"
                }
            ],
            "extraction_date": "2024-01-15T10:30:00",
            "processing_time": 3.5,
            "json_path": f"/exports/export_{process_id}.json",
            "csv_path": f"/exports/export_{process_id}.csv",
            "excel_path": f"/exports/export_{process_id}.xlsx",
            "preview_path": f"/previews/preview_{process_id}.png"
        }
        
        return ExtractionResult(**result_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ExtractionResult])
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des traitements
    """
    try:
        # Récupérer depuis la base de données avec pagination
        # results = db.query(...).offset((page-1)*limit).limit(limit).all()
        
        # Pour l'exemple, simuler des données
        results = []
        for i in range(min(limit, 10)):
            process_id = f"proc_{page}_{i}"
            results.append({
                "id": i + 1,
                "process_id": process_id,
                "document_id": i + 1,
                "user_id": 1,
                "extracted_data": {
                    "document_type": ["invoice", "receipt", "contract"][i % 3],
                    "status": "completed"
                },
                "confidence_score": 0.8 + (i * 0.02),
                "extraction_date": f"2024-01-{15+i:02d}T10:30:00",
                "processing_time": 2.5 + (i * 0.5)
            })
        
        return [ExtractionResult(**result) for result in results]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{process_id}/export", response_model=ExportResponse)
async def export_result(
    process_id: str,
    format: str = Query("json", regex="^(json|csv|excel|pdf)$"),
    db: Session = Depends(get_db)
):
    """
    Exporte les résultats dans un format spécifique
    """
    try:
        # Vérifier si le processus existe
        # result = db.query(...).filter(...).first()
        
        if not process_id:
            raise HTTPException(status_code=404, detail="Processus non trouvé")
        
        # Déterminer le chemin du fichier d'export
        export_dir = os.path.join(settings.UPLOAD_DIR, "exports")
        base_filename = f"export_{process_id}"
        
        if format == "json":
            filename = f"{base_filename}.json"
            content_type = "application/json"
        elif format == "csv":
            filename = f"{base_filename}.csv"
            content_type = "text/csv"
        elif format == "excel":
            filename = f"{base_filename}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            filename = f"{base_filename}.pdf"
            content_type = "application/pdf"
        
        file_path = os.path.join(export_dir, filename)
        
        # Vérifier si le fichier existe
        if not os.path.exists(file_path):
            # Générer le fichier d'export
            from app.utils.export_utils import ExportUtils
            
            # Récupérer les données
            result_data = {
                "process_id": process_id,
                "data": {"test": "data"},
                "export_date": "2024-01-15"
            }
            
            if format == "json":
                ExportUtils.to_json(result_data, file_path)
            elif format == "csv":
                ExportUtils.to_csv(result_data, file_path)
            elif format == "excel":
                ExportUtils.to_excel(result_data, file_path)
        
        # Retourner la réponse
        return ExportResponse(
            success=True,
            format=format,
            filename=filename,
            download_url=f"/api/results/{process_id}/download/{format}",
            file_size=os.path.getsize(file_path)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{process_id}/download/{format}")
async def download_export(
    process_id: str,
    format: str,
    db: Session = Depends(get_db)
):
    """
    Télécharge un fichier exporté
    """
    try:
        # Déterminer le chemin du fichier
        export_dir = os.path.join(settings.UPLOAD_DIR, "exports")
        base_filename = f"export_{process_id}"
        
        if format == "json":
            filename = f"{base_filename}.json"
            media_type = "application/json"
        elif format == "csv":
            filename = f"{base_filename}.csv"
            media_type = "text/csv"
        elif format == "excel":
            filename = f"{base_filename}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            filename = f"{base_filename}.pdf"
            media_type = "application/pdf"
        
        file_path = os.path.join(export_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{process_id}")
async def delete_result(
    process_id: str,
    db: Session = Depends(get_db)
):
    """
    Supprime un résultat
    """
    try:
        # Supprimer de la base de données
        # db.query(...).filter(...).delete()
        # db.commit()
        
        return {
            "success": True,
            "message": f"Résultat {process_id} supprimé"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
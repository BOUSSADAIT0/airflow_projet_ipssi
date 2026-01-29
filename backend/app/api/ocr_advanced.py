from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
import uuid
import os
import json
import pandas as pd
from datetime import datetime
import logging

from app.utils.ocr_processor_advanced import AdvancedOCRProcessor
from app.config import settings

router = APIRouter(prefix="/api/ocr", tags=["OCR Avancé"])
logger = logging.getLogger(__name__)

# Initialiser le processeur OCR avancé
ocr_processor = AdvancedOCRProcessor(
    tesseract_path=settings.TESSERACT_PATH,
    default_language=settings.DEFAULT_LANGUAGE
)

@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    language: str = Form("fra+eng"),
    extract_entities: bool = Form(True)
):
    """
    Traite un document avec OCR avancé
    """
    try:
        # Vérifier le fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # Lire le contenu
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Fichier vide")
        
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10MB)")
        
        # Traitement OCR
        logger.info(f"Traitement du fichier: {file.filename}")
        result = ocr_processor.process_file(content, file.filename, language)
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur OCR: {result.get('error', 'Erreur inconnue')}"
            )
        
        # Générer un ID de processus
        process_id = str(uuid.uuid4())
        
        # Sauvegarder les résultats
        result['process_id'] = process_id
        result['upload_timestamp'] = datetime.now().isoformat()
        
        # Sauvegarder en JSON
        save_result(result, process_id)
        
        return {
            "success": True,
            "process_id": process_id,
            "message": "Document traité avec succès",
            "result": {
                "filename": result['filename'],
                "document_type": result['document_type'],
                "total_pages": result['total_pages'],
                "average_confidence": result['average_confidence'],
                "entities_found": len(result['structured_data'].get('entities', {})),
                "personal_info": result['structured_data'].get('personal_info', {}),
                "preview_url": f"/api/ocr/results/{process_id}/preview"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur traitement: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.post("/batch-process")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    language: str = Form("fra+eng")
):
    """
    Traite plusieurs documents en batch
    """
    try:
        results = []
        process_ids = []
        
        for file in files:
            try:
                content = await file.read()
                
                # Traitement
                result = ocr_processor.process_file(content, file.filename, language)
                
                if result['success']:
                    process_id = str(uuid.uuid4())
                    result['process_id'] = process_id
                    save_result(result, process_id)
                    
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "process_id": process_id,
                        "document_type": result['document_type'],
                        "pages": result['total_pages'],
                        "confidence": result['average_confidence']
                    })
                    process_ids.append(process_id)
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": result.get('error', 'Erreur inconnue')
                    })
                
                # Réinitialiser pour le prochain fichier
                await file.seek(0)
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_files": len(files),
            "processed_files": len([r for r in results if r['success']]),
            "failed_files": len([r for r in results if not r['success']]),
            "results": results,
            "batch_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur batch: {str(e)}")

@router.get("/results/{process_id}")
async def get_results(process_id: str):
    """
    Récupère les résultats d'un traitement
    """
    try:
        result = load_result(process_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Résultats non trouvés")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{process_id}/download/{format}")
async def download_results(
    process_id: str,
    format: str  # json, csv, txt
):
    """
    Télécharge les résultats dans différents formats
    """
    try:
        result = load_result(process_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Résultats non trouvés")
        
        filename = f"ocr_result_{process_id}"
        
        if format == "json":
            content = json.dumps(result, indent=2, ensure_ascii=False)
            content_type = "application/json"
            filename += ".json"
            
        elif format == "csv":
            # Convertir en CSV structuré
            csv_data = convert_to_csv(result)
            content = csv_data
            content_type = "text/csv"
            filename += ".csv"
            
        elif format == "txt":
            content = result.get('text', '')
            content_type = "text/plain"
            filename += ".txt"
            
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
        
        # Sauvegarder temporairement
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type=content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{process_id}/preview")
async def get_preview(process_id: str):
    """
    Retourne un aperçu des résultats
    """
    try:
        result = load_result(process_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Résultats non trouvés")
        
        # Préparer l'aperçu
        preview = {
            "process_id": process_id,
            "filename": result.get('filename'),
            "document_type": result.get('document_type'),
            "total_pages": result.get('total_pages'),
            "confidence": result.get('average_confidence'),
            "processing_date": result.get('metadata', {}).get('processing_date'),
            "entities": result.get('structured_data', {}).get('entities', {}),
            "personal_info": result.get('structured_data', {}).get('personal_info', {}),
            "text_preview": result.get('text', '')[:500] + "..." if len(result.get('text', '')) > 500 else result.get('text', ''),
            "download_urls": {
                "json": f"/api/ocr/results/{process_id}/download/json",
                "csv": f"/api/ocr/results/{process_id}/download/csv",
                "txt": f"/api/ocr/results/{process_id}/download/txt"
            }
        }
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats():
    """
    Retourne des statistiques sur les traitements
    """
    try:
        # Compter les fichiers dans le dossier results
        results_dir = "results"
        if not os.path.exists(results_dir):
            return {"total_processed": 0, "by_type": {}}
        
        files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        
        # Analyser les types de documents
        doc_types = {}
        for file in files[:100]:  # Limiter pour la performance
            try:
                with open(os.path.join(results_dir, file), 'r') as f:
                    data = json.load(f)
                    doc_type = data.get('document_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            except:
                continue
        
        return {
            "total_processed": len(files),
            "by_document_type": doc_types,
            "last_processed": sorted(files, reverse=True)[:5] if files else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fonctions utilitaires
def save_result(result: dict, process_id: str):
    """Sauvegarde les résultats en JSON"""
    os.makedirs("results", exist_ok=True)
    
    filepath = f"results/{process_id}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Résultats sauvegardés: {filepath}")

def load_result(process_id: str) -> Optional[dict]:
    """Charge les résultats depuis le JSON"""
    filepath = f"results/{process_id}.json"
    
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def convert_to_csv(result: dict) -> str:
    """Convertit les résultats en CSV"""
    import io
    
    # Créer un DataFrame avec les données structurées
    data = {
        'Champ': [],
        'Valeur': [],
        'Confidence': [],
        'Type': []
    }
    
    # Informations de base
    data['Champ'].extend(['Nom du fichier', 'Type de document', 'Pages', 'Confiance moyenne'])
    data['Valeur'].extend([
        result.get('filename', ''),
        result.get('document_type', ''),
        str(result.get('total_pages', 0)),
        str(result.get('average_confidence', 0))
    ])
    data['Confidence'].extend(['N/A', 'N/A', 'N/A', 'N/A'])
    data['Type'].extend(['metadata', 'metadata', 'metadata', 'metadata'])
    
    # Informations personnelles
    personal_info = result.get('structured_data', {}).get('personal_info', {})
    for key, value in personal_info.items():
        if value:
            data['Champ'].append(f"Info Personnelle - {key}")
            data['Valeur'].append(str(value))
            data['Confidence'].append('N/A')
            data['Type'].append('personal_info')
    
    # Entités extraites
    entities = result.get('structured_data', {}).get('entities', {})
    for entity_type, values in entities.items():
        if isinstance(values, list):
            for i, value in enumerate(values[:10]):  # Limiter à 10 par type
                data['Champ'].append(f"Entité - {entity_type} {i+1}")
                data['Valeur'].append(str(value))
                data['Confidence'].append('N/A')
                data['Type'].append('entity')
    
    # Créer le DataFrame
    df = pd.DataFrame(data)
    
    # Écrire en CSV
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    
    return output.getvalue()
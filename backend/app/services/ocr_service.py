# app/api/ocr.py
import pytesseract
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from PIL import Image
import io

# Importez settings depuis app.config
from app.config import settings

# Configurez pytesseract avec le chemin depuis settings
# Vérifiez d'abord si TESSERACT_PATH est défini
if hasattr(settings, 'TESSERACT_PATH') and settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

router = APIRouter()

# Importez OCRService (corrigez selon votre choix précédent)
from app.services.ocr_service import OCRService
ocr_service = OCRService()

@router.post("/ocr")
async def extract_text(
    file: UploadFile = File(...),
    language: str = "fra+eng"
):
    """
    Endpoint OCR pour extraire le texte d'une image
    """
    try:
        # Lire le contenu du fichier
        contents = await file.read()
        
        # Vérifier que c'est une image
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="Le fichier doit être une image"
            )
        
        # Utiliser OCRService
        result = ocr_service.process_single_file(contents, file.filename, language)
        
        # Si vous préférez une version simple sans OCRService :
        # text = simple_ocr_extract(contents, language)
        # return {"filename": file.filename, "text": text}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR: {str(e)}")

@router.post("/ocr/async")
async def extract_text_async(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Version asynchrone du traitement OCR"""
    try:
        contents = await file.read()
        result = await ocr_service.process_async(
            contents, 
            file.filename,
            background_tasks=background_tasks
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ocr/status/{process_id}")
async def get_status(process_id: str):
    """Récupère le statut d'un traitement"""
    status = await ocr_service.get_processing_status(process_id)
    return status

# Fonction OCR simple alternative (en cas de problème avec OCRService)
def simple_ocr_extract(image_bytes: bytes, language: str = "fra+eng") -> str:
    """
    Fonction OCR simple utilisant pytesseract directement
    """
    try:
        # Ouvrir l'image depuis les bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convertir en niveaux de gris si nécessaire
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extraire le texte
        text = pytesseract.image_to_string(image, lang=language)
        
        return text.strip()
        
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction OCR: {str(e)}")
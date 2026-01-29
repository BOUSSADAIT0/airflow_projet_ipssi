import os
import io
import json
import csv
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Import des modules OCR
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    from pdf2image import convert_from_bytes
    import pandas as pd
    OCR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Module manquant: {e}")
    OCR_AVAILABLE = False

app = FastAPI(title="OCR Intelligent API", version="1.0.0")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les répertoires nécessaires
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Modèles Pydantic
class OCRResult(BaseModel):
    filename: str
    document_type: str
    extracted_data: Dict[str, Any]
    confidence: float
    processing_time: float
    preview_path: str = None

class ExportRequest(BaseModel):
    format: str = "json"

# Classes de traitement OCR
class ImagePreprocessor:
    """Classe pour le prétraitement des images"""
    
    def __init__(self):
        self.min_width = 500
        self.min_height = 500
    
    def load_image(self, file_bytes: bytes, filename: str):
        """Charge une image depuis des bytes"""
        try:
            if filename.lower().endswith('.pdf'):
                # Conversion PDF en image
                images = convert_from_bytes(file_bytes)
                if images:
                    return np.array(images[0])
                return None
            
            # Pour les images
            nparr = np.frombuffer(file_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
        except Exception as e:
            print(f"Erreur de chargement: {e}")
            return None
    
    def preprocess(self, image):
        """Prétraitement de l'image"""
        if image is None:
            return None
        
        # Conversion en niveaux de gris
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Réduction du bruit
        denoised = cv2.medianBlur(gray, 3)
        
        # Binarisation (seuillage d'Otsu)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Amélioration du contraste (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(binary)
        
        return enhanced
    
    def detect_text_regions(self, image):
        """Détecte les régions de texte"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Binarisation inversée pour la détection de texte
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Dilation pour regrouper les caractères
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        dilated = cv2.dilate(binary, kernel, iterations=3)
        
        # Recherche des contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 50 and h > 20:  # Filtre les petites zones
                regions.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'type': 'text'
                })
        
        return regions
    
    def detect_tables(self, image):
        """Détecte les zones de tableau"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Détection des lignes horizontales
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Détection des lignes verticales
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combinaison des lignes
        table_structure = cv2.add(horizontal_lines, vertical_lines)
        
        # Recherche des contours
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 100 and h > 100:  # Filtre les petites zones
                tables.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'type': 'table'
                })
        
        return tables

class OCREngine:
    """Moteur OCR utilisant Tesseract"""
    
    def __init__(self, language: str = "fra+eng"):
        self.language = language
    
    def extract_text(self, image):
        """Extrait le texte d'une image"""
        try:
            # Conversion PIL Image si nécessaire
            if isinstance(image, np.ndarray):
                if len(image.shape) == 2:  # Grayscale
                    pil_image = Image.fromarray(image)
                else:  # Couleur
                    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = image
            
            # Configuration Tesseract
            custom_config = r'--oem 3 --psm 3'
            
            # Extraction du texte
            text = pytesseract.image_to_string(pil_image, lang=self.language, config=custom_config)
            
            # Extraction avec détails pour la confiance
            data = pytesseract.image_to_data(pil_image, lang=self.language, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Calcul de la confiance moyenne
            confidences = [float(conf) for conf in data['conf'] if float(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            print(f"Erreur OCR: {e}")
            return "", 0.0
    
    def extract_from_regions(self, image, regions):
        """Extrait le texte de régions spécifiques"""
        results = []
        for region in regions:
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            
            # Découpage de la région
            if len(image.shape) == 2:
                region_img = image[y:y+h, x:x+w]
            else:
                region_img = image[y:y+h, x:x+w, :]
            
            if region_img.size == 0:
                continue
            
            # Extraction OCR
            text, confidence = self.extract_text(region_img)
            
            if text:
                results.append({
                    'region': region,
                    'text': text,
                    'confidence': confidence
                })
        
        return results

class SemanticExtractor:
    """Extracteur sémantique pour identifier les champs utiles"""
    
    def __init__(self):
        # Modèles de regex pour la détection
        self.patterns = {
            'date': [
                r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
                r'\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b',
                r'\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b'
            ],
            'montant': [
                r'\b\d{1,3}(?:\s?\d{3})*(?:[.,]\d{1,2})?\s*[€$£]\b',
                r'\b(?:total|montant|TOTAL|MONTANT)\s*[:.]?\s*([\d\s.,]+[€$£]?)'
            ],
            'email': [
                r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            ],
            'telephone': [
                r'\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b',
                r'\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b'
            ],
            'numero_facture': [
                r'\b(?:facture|invoice|n°|no|numéro)[\s:.-]*([A-Z0-9-]+)\b',
                r'\b(?:FACT|INV|CMD|BLL)-?\d{4,10}\b'
            ],
            'tva': [
                r'\b(?:TVA|tva)[\s:.-]*(\d{1,3}(?:[.,]\d{1,2})?%?)\b'
            ]
        }
    
    def extract_fields(self, text):
        """Extrait les champs sémantiques du texte"""
        import re
        
        fields = {}
        
        for field_name, patterns in self.patterns.items():
            field_values = []
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.groups() else match.group()
                    field_values.append({
                        'value': value,
                        'position': match.span(),
                        'confidence': 0.8  # Confiance par défaut
                    })
            
            if field_values:
                fields[field_name] = field_values
        
        return fields
    
    def detect_document_type(self, text):
        """Détecte le type de document"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['facture', 'invoice', 'montant', 'tva', 'client']):
            return 'facture'
        elif any(word in text_lower for word in ['cv', 'curriculum', 'expérience', 'compétence']):
            return 'cv'
        elif any(word in text_lower for word in ['contrat', 'article', 'clause', 'signature']):
            return 'contrat'
        elif any(word in text_lower for word in ['formulaire', 'nom', 'prénom', 'adresse']):
            return 'formulaire'
        else:
            return 'document'

class OCRPipeline:
    """Pipeline complet de traitement OCR"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = OCREngine()
        self.semantic_extractor = SemanticExtractor()
    
    def process(self, file_bytes: bytes, filename: str):
        """Traite un document complet"""
        import time
        start_time = time.time()
        
        try:
            print(f"📄 Traitement de: {filename}")
            
            # 1. Chargement de l'image
            original_image = self.preprocessor.load_image(file_bytes, filename)
            if original_image is None:
                raise ValueError("Impossible de charger l'image")
            
            # 2. Prétraitement
            print("  🔧 Prétraitement...")
            processed_image = self.preprocessor.preprocess(original_image)
            
            # 3. Détection de zones
            print("  📍 Détection de zones...")
            text_regions = self.preprocessor.detect_text_regions(processed_image)
            table_regions = self.preprocessor.detect_tables(processed_image)
            all_regions = text_regions + table_regions
            
            # 4. OCR sur l'image complète
            print("  🔤 Extraction OCR...")
            full_text, full_confidence = self.ocr_engine.extract_text(processed_image)
            
            # 5. OCR par régions
            region_results = self.ocr_engine.extract_from_regions(processed_image, all_regions)
            
            # 6. Extraction sémantique
            print("  🧠 Extraction sémantique...")
            fields = self.semantic_extractor.extract_fields(full_text)
            doc_type = self.semantic_extractor.detect_document_type(full_text)
            
            # 7. Structuration des données
            print("  📊 Structuration des données...")
            processing_time = time.time() - start_time
            
            # Sauvegarde d'un aperçu
            preview_filename = f"{uuid.uuid4()}_preview.jpg"
            preview_path = os.path.join("uploads", preview_filename)
            cv2.imwrite(preview_path, original_image)
            
            # Construction du résultat
            result = {
                'filename': filename,
                'document_type': doc_type,
                'confidence': full_confidence,
                'processing_time': processing_time,
                'preview_path': f"/uploads/{preview_filename}",
                'metadata': {
                    'image_size': original_image.shape,
                    'region_count': len(all_regions),
                    'text_length': len(full_text)
                },
                'regions': region_results,
                'extracted_fields': fields,
                'full_text': full_text
            }
            
            print(f"  ✅ Traitement terminé en {processing_time:.2f}s")
            return result
            
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            raise

# Initialiser le pipeline OCR
ocr_pipeline = OCRPipeline() if OCR_AVAILABLE else None

# Routes API
@app.get("/")
async def root():
    return {
        "app": "OCR Intelligent API",
        "version": "1.0.0",
        "status": "running",
        "ocr_available": OCR_AVAILABLE,
        "endpoints": {
            "upload": "POST /api/upload",
            "export": "POST /api/export/{filename}",
            "list": "GET /api/files",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "ocr": OCR_AVAILABLE}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Endpoint pour uploader et traiter un document"""
    try:
        if not OCR_AVAILABLE:
            raise HTTPException(500, "OCR non disponible. Vérifiez les dépendances.")
        
        # Vérifier l'extension
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(400, f"Format non supporté. Formats autorisés: {', '.join(allowed_extensions)}")
        
        # Lire le fichier
        contents = await file.read()
        
        # Traitement OCR
        result = ocr_pipeline.process(contents, file.filename)
        
        # Sauvegarde des résultats
        result_id = str(uuid.uuid4())
        result_filename = f"{result_id}_{file.filename}"
        
        # Sauvegarde JSON
        json_path = os.path.join("results", f"{result_id}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Sauvegarde CSV
        csv_path = os.path.join("results", f"{result_id}.csv")
        self._save_to_csv(result, csv_path)
        
        # Mise à jour du résultat
        result['result_id'] = result_id
        result['json_url'] = f"/api/results/{result_id}/json"
        result['csv_url'] = f"/api/results/{result_id}/csv"
        
        return result
        
    except Exception as e:
        raise HTTPException(500, f"Erreur de traitement: {str(e)}")

@app.get("/api/results/{result_id}/json")
async def get_json_result(result_id: str):
    """Récupère le résultat au format JSON"""
    json_path = os.path.join("results", f"{result_id}.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(404, "Résultat non trouvé")
    
    return FileResponse(
        path=json_path,
        filename=f"ocr_result_{result_id}.json",
        media_type="application/json"
    )

@app.get("/api/results/{result_id}/csv")
async def get_csv_result(result_id: str):
    """Récupère le résultat au format CSV"""
    csv_path = os.path.join("results", f"{result_id}.csv")
    
    if not os.path.exists(csv_path):
        raise HTTPException(404, "Résultat non trouvé")
    
    return FileResponse(
        path=csv_path,
        filename=f"ocr_result_{result_id}.csv",
        media_type="text/csv"
    )

@app.get("/api/files")
async def list_files():
    """Liste tous les fichiers traités"""
    files = []
    
    for filename in os.listdir("results"):
        if filename.endswith('.json'):
            file_path = os.path.join("results", filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                files.append({
                    'id': filename.replace('.json', ''),
                    'filename': data.get('filename', ''),
                    'type': data.get('document_type', ''),
                    'confidence': data.get('confidence', 0),
                    'date': os.path.getmtime(file_path)
                })
    
    return files

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Accède aux fichiers uploadés"""
    file_path = os.path.join("uploads", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, "Fichier non trouvé")
    
    return FileResponse(file_path)

def _save_to_csv(self, result: Dict, csv_path: str):
    """Sauvegarde les résultats en CSV"""
    try:
        # Préparation des données pour CSV
        rows = []
        
        # Champs extraits
        for field_name, field_values in result.get('extracted_fields', {}).items():
            for field_value in field_values:
                rows.append({
                    'type': 'field',
                    'category': field_name,
                    'value': field_value.get('value', ''),
                    'confidence': field_value.get('confidence', 0)
                })
        
        # Régions détectées
        for region in result.get('regions', []):
            rows.append({
                'type': 'region',
                'category': region.get('region', {}).get('type', ''),
                'value': region.get('text', ''),
                'confidence': region.get('confidence', 0),
                'position': f"{region.get('region', {}).get('x', 0)},{region.get('region', {}).get('y', 0)}"
            })
        
        # Métadonnées
        rows.append({
            'type': 'metadata',
            'category': 'document_type',
            'value': result.get('document_type', ''),
            'confidence': result.get('confidence', 0)
        })
        
        # Création du DataFrame et sauvegarde
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde CSV: {e}")

# Servir les fichiers statiques
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

if __name__ == "__main__":
    print("🚀 Démarrage du serveur OCR Intelligent...")
    print("📡 API: http://localhost:8000")
    print("📚 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
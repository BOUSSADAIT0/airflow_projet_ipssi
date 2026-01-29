import pytesseract
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
from app.config import settings

@dataclass
class OCRResult:
    """Résultat d'extraction OCR"""
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    page_num: int = 1

class OCREngine:
    """Moteur OCR utilisant Tesseract"""
    
    def __init__(self, language: str = None):
        self.language = language or settings.DEFAULT_LANGUAGE
        
        # Configuration Tesseract
        if settings.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
        
        # Configuration OCR
        self.configs = {
            'default': '--oem 3 --psm 3',
            'single_column': '--oem 3 --psm 4',
            'single_line': '--oem 3 --psm 7',
            'single_word': '--oem 3 --psm 8',
            'sparse_text': '--oem 3 --psm 11',
            'sparse_text_osd': '--oem 3 --psm 12'
        }
    
    def extract_text(self, image: np.ndarray, config: str = 'default') -> str:
        """Extrait le texte d'une image complète"""
        try:
            # Conversion en RGB si nécessaire
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extraction du texte
            text = pytesseract.image_to_string(
                image_rgb,
                lang=self.language,
                config=self.configs[config]
            )
            return text.strip()
        except Exception as e:
            print(f"Erreur d'extraction OCR: {e}")
            return ""
    
    def extract_with_details(self, image: np.ndarray, config: str = 'default') -> List[OCRResult]:
        """Extrait le texte avec détails (boîtes englobantes, confiance)"""
        try:
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extraction détaillée
            data = pytesseract.image_to_data(
                image_rgb,
                lang=self.language,
                config=self.configs[config],
                output_type=pytesseract.Output.DICT
            )
            
            results = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = float(data['conf'][i]) / 100.0  # Normalisation 0-1
                
                if text and conf >= settings.CONFIDENCE_THRESHOLD:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    result = OCRResult(
                        text=text,
                        confidence=conf,
                        bounding_box=(x, y, w, h)
                    )
                    results.append(result)
            
            return results
        except Exception as e:
            print(f"Erreur d'extraction détaillée OCR: {e}")
            return []
    
    def extract_from_zone(self, image: np.ndarray, zone: Tuple[int, int, int, int], 
                         config: str = 'default') -> str:
        """Extrait le texte d'une zone spécifique"""
        x, y, w, h = zone
        
        # Découpage de la zone
        if len(image.shape) == 2:
            zone_img = image[y:y+h, x:x+w]
        else:
            zone_img = image[y:y+h, x:x+w, :]
        
        if zone_img.size == 0:
            return ""
        
        return self.extract_text(zone_img, config)
    
    def detect_orientation(self, image: np.ndarray) -> Dict[str, Any]:
        """Détecte l'orientation du document"""
        try:
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Détection d'orientation et de script
            osd = pytesseract.image_to_osd(
                image_rgb,
                config='--psm 0',
                output_type=pytesseract.Output.DICT
            )
            
            return {
                'rotation': osd.get('rotate', 0),
                'orientation': osd.get('orientation', 0),
                'script': osd.get('script', ''),
                'script_confidence': osd.get('script_confidence', 0)
            }
        except Exception as e:
            print(f"Erreur de détection d'orientation: {e}")
            return {'rotation': 0, 'orientation': 0, 'script': '', 'script_confidence': 0}
    
    def extract_tables(self, image: np.ndarray) -> List[List[str]]:
        """Extrait les données tabulaires"""
        try:
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extraction avec détection de structure
            data = pytesseract.image_to_data(
                image_rgb,
                lang=self.language,
                config='--oem 3 --psm 6',
                output_type=pytesseract.Output.DICT
            )
            
            # Organisation par lignes basée sur les coordonnées Y
            rows = {}
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text:
                    continue
                
                y = data['top'][i]
                x = data['left'][i]
                
                # Regroupement par ligne (tolérance de 10 pixels)
                row_key = (y // 10) * 10
                
                if row_key not in rows:
                    rows[row_key] = []
                
                rows[row_key].append({
                    'text': text,
                    'x': x,
                    'confidence': float(data['conf'][i]) / 100.0
                })
            
            # Tri par position X et création du tableau
            table = []
            for row_key in sorted(rows.keys()):
                row_items = sorted(rows[row_key], key=lambda item: item['x'])
                row = [item['text'] for item in row_items]
                table.append(row)
            
            return table
        except Exception as e:
            print(f"Erreur d'extraction de tableau: {e}")
            return []
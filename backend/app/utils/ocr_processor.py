import pytesseract
from PIL import Image
import pdf2image
import io
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, tesseract_path: str = None, default_language: str = "fra+eng"):
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.default_language = default_language
    
    def process_file(self, file_content: bytes, filename: str, language: str = None) -> Dict[str, Any]:
        """Traite un fichier et extrait le texte"""
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Convertir en images si nécessaire
            if file_ext == '.pdf':
                try:
                    images = pdf2image.convert_from_bytes(file_content, dpi=200)
                except Exception as e:
                    logger.error(f"Erreur conversion PDF: {str(e)}")
                    return self._create_error_response(f"Erreur PDF: {str(e)}")
            else:
                try:
                    image = Image.open(io.BytesIO(file_content))
                    images = [image]
                except Exception as e:
                    logger.error(f"Erreur chargement image: {str(e)}")
                    return self._create_error_response(f"Erreur image: {str(e)}")
            
            results = []
            total_text = ""
            
            for i, image in enumerate(images):
                # Convertir en RGB pour éviter les problèmes
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Extraction OCR
                try:
                    text = pytesseract.image_to_string(
                        image, 
                        lang=language or self.default_language,
                        config='--oem 3 --psm 3'
                    )
                    
                    # Obtenir les données détaillées pour la confiance
                    data = pytesseract.image_to_data(
                        image,
                        lang=language or self.default_language,
                        config='--oem 3 --psm 3',
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Calculer la confiance moyenne
                    confidences = [int(c) for c in data['conf'] if int(c) > 0]
                    avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0
                    
                    results.append({
                        'page': i + 1,
                        'text': text,
                        'confidence': avg_confidence
                    })
                    total_text += f"--- Page {i+1} ---\n{text}\n\n"
                    
                except Exception as e:
                    logger.error(f"Erreur OCR page {i+1}: {str(e)}")
                    results.append({
                        'page': i + 1,
                        'text': '',
                        'confidence': 0,
                        'error': str(e)
                    })
            
            # Analyse simple
            structured_data = self._analyze_text(total_text, filename)
            
            return {
                'success': True,
                'text': total_text,
                'pages': results,
                'structured_data': structured_data,
                'total_pages': len(images),
                'average_confidence': sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur générale OCR: {str(e)}")
            return self._create_error_response(str(e))
    
    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Crée une réponse d'erreur standardisée"""
        return {
            'success': False,
            'error': error_msg,
            'text': '',
            'structured_data': {},
            'total_pages': 0,
            'average_confidence': 0
        }
    
    def _analyze_text(self, text: str, filename: str) -> Dict[str, Any]:
        """Analyse simple du texte"""
        import re
        
        structured_data = {
            'document_type': self._detect_document_type(filename, text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'character_count': len(text),
            'dates_found': [],
            'emails_found': [],
            'phones_found': []
        }
        
        # Recherche de dates
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{4}/\d{1,2}/\d{1,2}'
        ]
        for pattern in date_patterns:
            structured_data['dates_found'].extend(re.findall(pattern, text))
        
        # Recherche d'emails
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if emails:
            structured_data['emails_found'] = list(set(emails))
        
        # Recherche de téléphones
        phones = re.findall(r'[\+\(]?[0-9][0-9\-\(\)\.]{8,}[0-9]', text)
        if phones:
            structured_data['phones_found'] = list(set(phones))
        
        return structured_data
    
    def _detect_document_type(self, filename: str, text: str) -> str:
        """Détecte le type de document"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        keywords = {
            'invoice': ['facture', 'invoice', 'bill', 'montant', 'total', '€', '$'],
            'receipt': ['reçu', 'receipt', 'ticket', 'caisse', 'paiement'],
            'contract': ['contrat', 'contract', 'agreement', 'signature'],
            'letter': ['lettre', 'letter', 'cher', 'madame', 'monsieur'],
            'report': ['rapport', 'report', 'analyse', 'conclusion']
        }
        
        for doc_type, words in keywords.items():
            if any(word in filename_lower for word in words):
                return doc_type
            if any(word in text_lower for word in words):
                return doc_type
        
        return 'document'
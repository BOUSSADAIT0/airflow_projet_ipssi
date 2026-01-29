# app/utils/ocr_processor_enhanced.py
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
from pdf2image import convert_from_bytes
import logging
from typing import Dict, List, Optional, Tuple, Union
import tempfile
import os
from skimage import exposure
import imutils

logger = logging.getLogger(__name__)

class EnhancedOCRProcessor:
    """
    Processeur OCR amélioré pour traiter tous types d'images
    - Images basse qualité
    - Images floues
    - Images avec faible contraste
    - Documents scannés
    - Photographies de documents
    """
    
    def __init__(self, tesseract_path: str = None, default_language: str = "fra+eng"):
        """
        Initialise le processeur OCR
        
        Args:
            tesseract_path: Chemin vers l'exécutable Tesseract
            default_language: Langues par défaut pour OCR
        """
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.default_language = default_language
        self.supported_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']
        
    def process_file(self, file_content: bytes, filename: str, language: str = None) -> Dict:
        """
        Traite un fichier avec OCR amélioré
        
        Args:
            file_content: Contenu du fichier en bytes
            filename: Nom du fichier
            language: Langue pour OCR (par défaut: fra+eng)
        
        Returns:
            Dict avec les résultats de l'OCR
        """
        try:
            language = language or self.default_language
            
            # Vérifier le format du fichier
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Format non supporté: {file_ext}")
            
            # Traitement selon le type de fichier
            if file_ext == '.pdf':
                images = self._convert_pdf_to_images(file_content)
            else:
                images = [self._load_image(file_content)]
            
            all_results = []
            total_confidence = 0
            page_count = len(images)
            
            for i, image in enumerate(images):
                page_result = self._process_image_page(image, i+1, language)
                all_results.append(page_result)
                total_confidence += page_result.get('confidence', 0)
            
            # Combiner les résultats
            combined_text = "\n\n--- Page {} ---\n\n".join(
                [f"Page {i+1}" for i in range(page_count)]
            )
            
            average_confidence = total_confidence / page_count if page_count > 0 else 0
            
            # Détecter le type de document
            document_type = self._detect_document_type(combined_text)
            
            # Extraire les données structurées
            structured_data = self._extract_structured_data(combined_text, document_type)
            
            return {
                'success': True,
                'filename': filename,
                'document_type': document_type,
                'total_pages': page_count,
                'text': combined_text,
                'pages': all_results,
                'average_confidence': average_confidence,
                'structured_data': structured_data,
                'metadata': {
                    'language': language,
                    'format': file_ext,
                    'processing_method': 'enhanced_ocr'
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement OCR: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename,
                'text': '',
                'pages': []
            }
    
    def _convert_pdf_to_images(self, pdf_content: bytes) -> List[Image.Image]:
        """Convertit un PDF en images"""
        try:
            images = convert_from_bytes(
                pdf_content,
                dpi=300,  # Haute résolution pour meilleur OCR
                fmt='jpeg',
                thread_count=4
            )
            return images
        except Exception as e:
            logger.error(f"Erreur conversion PDF: {str(e)}")
            raise
    
    def _load_image(self, image_content: bytes) -> Image.Image:
        """Charge une image depuis bytes"""
        try:
            return Image.open(io.BytesIO(image_content))
        except Exception as e:
            logger.error(f"Erreur chargement image: {str(e)}")
            raise
    
    def _process_image_page(self, image: Image.Image, page_num: int, language: str) -> Dict:
        """Traite une seule page/image avec différentes méthodes OCR"""
        
        # Convertir PIL Image en OpenCV
        open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Liste pour stocker les résultats des différentes méthodes
        all_results = []
        
        # Méthode 1: OCR sur image originale
        orig_text, orig_conf = self._ocr_on_image(open_cv_image, language)
        all_results.append((orig_text, orig_conf, 'original'))
        
        # Méthode 2: OCR sur image en niveaux de gris
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        gray_text, gray_conf = self._ocr_on_image(gray, language)
        all_results.append((gray_text, gray_conf, 'gray'))
        
        # Méthode 3: OCR après amélioration de contraste
        enhanced_contrast = self._enhance_contrast(gray)
        contrast_text, contrast_conf = self._ocr_on_image(enhanced_contrast, language)
        all_results.append((contrast_text, contrast_conf, 'contrast_enhanced'))
        
        # Méthode 4: OCR après binarisation (seuillage)
        binary = self._adaptive_threshold(gray)
        binary_text, binary_conf = self._ocr_on_image(binary, language)
        all_results.append((binary_text, binary_conf, 'binary'))
        
        # Méthode 5: OCR après réduction du bruit
        denoised = self._denoise_image(gray)
        denoised_text, denoised_conf = self._ocr_on_image(denoised, language)
        all_results.append((denoised_text, denoised_conf, 'denoised'))
        
        # Méthode 6: OCR après redressement (deskew)
        deskewed = self._deskew_image(gray)
        deskewed_text, deskewed_conf = self._ocr_on_image(deskewed, language)
        all_results.append((deskewed_text, deskewed_conf, 'deskewed'))
        
        # Méthode 7: OCR après amélioration de la netteté
        sharpened = self._sharpen_image(gray)
        sharpened_text, sharpened_conf = self._ocr_on_image(sharpened, language)
        all_results.append((sharpened_text, sharpened_conf, 'sharpened'))
        
        # Méthode 8: OCR après égalisation d'histogramme
        equalized = self._histogram_equalization(gray)
        equalized_text, equalized_conf = self._ocr_on_image(equalized, language)
        all_results.append((equalized_text, equalized_conf, 'equalized'))
        
        # Méthode 9: OCR après super-résolution (upscaling pour images basse qualité)
        upscaled = self._upscale_image(gray)
        upscaled_text, upscaled_conf = self._ocr_on_image(upscaled, language)
        all_results.append((upscaled_text, upscaled_conf, 'upscaled'))
        
        # Choisir le meilleur résultat
        best_result = max(all_results, key=lambda x: x[1])
        best_text, best_conf, method_used = best_result
        
        # Vérifier et améliorer la cohérence du texte
        cleaned_text = self._clean_ocr_text(best_text)
        
        return {
            'page_number': page_num,
            'text': cleaned_text,
            'confidence': best_conf,
            'method_used': method_used,
            'all_methods_results': [
                {'method': m, 'confidence': c, 'text_preview': t[:100]}
                for t, c, m in all_results
            ]
        }
    
    def _ocr_on_image(self, image, language: str) -> Tuple[str, float]:
        """Exécute OCR sur une image avec Tesseract"""
        try:
            # Configuration Tesseract optimisée
            custom_config = f'--oem 3 --psm 3 -l {language}'
            
            # Extraire le texte avec les données de confiance
            data = pytesseract.image_to_data(
                image, 
                config=custom_config, 
                output_type=pytesseract.Output.DICT
            )
            
            # Calculer la confiance moyenne
            confidences = [int(c) for c in data['conf'] if int(c) >= 0]
            avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0
            
            # Combiner le texte
            text = ' '.join([word for word, conf in zip(data['text'], data['conf']) 
                            if int(conf) >= 0 and word.strip()])
            
            return text, avg_confidence
            
        except Exception as e:
            logger.warning(f"Erreur OCR: {str(e)}")
            return "", 0.0
    
    def _enhance_contrast(self, image):
        """Améliore le contraste de l'image"""
        try:
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            return clahe.apply(image)
        except:
            # Fallback à l'égalisation d'histogramme simple
            return cv2.equalizeHist(image)
    
    def _adaptive_threshold(self, image):
        """Applique un seuillage adaptatif"""
        try:
            return cv2.adaptiveThreshold(
                image, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                11, 
                2
            )
        except:
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
    
    def _denoise_image(self, image):
        """Réduit le bruit de l'image"""
        try:
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        except:
            # Fallback à un flou gaussien
            return cv2.GaussianBlur(image, (3, 3), 0)
    
    def _deskew_image(self, image):
        """Redresse l'image inclinée"""
        try:
            # Détecter l'angle d'inclinaison
            coords = np.column_stack(np.where(image > 0))
            if len(coords) < 2:
                return image
                
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            
            # Rotation de l'image
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), 
                                    flags=cv2.INTER_CUBIC, 
                                    borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except:
            return image
    
    def _sharpen_image(self, image):
        """Améliore la netteté de l'image"""
        try:
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)
        except:
            return image
    
    def _histogram_equalization(self, image):
        """Applique l'égalisation d'histogramme"""
        try:
            return cv2.equalizeHist(image)
        except:
            return image
    
    def _upscale_image(self, image, scale_factor: float = 2.0):
        """Augmente la résolution de l'image"""
        try:
            height, width = image.shape[:2]
            new_height = int(height * scale_factor)
            new_width = int(width * scale_factor)
            
            return cv2.resize(image, (new_width, new_height), 
                            interpolation=cv2.INTER_CUBIC)
        except:
            return image
    
    def _clean_ocr_text(self, text: str) -> str:
        """Nettoie et améliore la qualité du texte OCR"""
        if not text:
            return ""
        
        # Supprimer les caractères non imprimables
        import re
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        
        # Corriger les erreurs OCR courantes
        replacements = {
            r'\b([A-Za-z])\s+([A-Za-z])\b': r'\1\2',  # Lettres séparées
            r'l\b': '1',  # l mal reconnu comme 1
            r'O\b': '0',  # O mal reconnu comme 0
            r'[|/]{2,}': 'l',  # || mal reconnu
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _detect_document_type(self, text: str) -> str:
        """Détecte le type de document basé sur le texte"""
        text_lower = text.lower()
        
        # Mots-clés pour différents types de documents
        document_patterns = {
            'facture': ['facture', 'invoice', 'fact.', 'inv.', 'client', 'total', 'tva'],
            'reçu': ['reçu', 'receipt', 'reçu de', 'caisse', 'ticket'],
            'contrat': ['contrat', 'contract', 'signé', 'parties', 'article'],
            'carte_identite': ['république', 'nationale', 'identité', 'carte'],
            'passeport': ['passeport', 'passport', 'autorité'],
            'formulaire': ['formulaire', 'form', 'date de naissance', 'adresse'],
            'relevé_bancaire': ['relevé', 'bancaire', 'compte', 'solde', 'débit'],
            'lettre': ['madame', 'monsieur', 'cher', 'objet', 'lettre'],
            'rapport': ['rapport', 'introduction', 'conclusion', 'chapitre'],
        }
        
        for doc_type, keywords in document_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return 'document_generique'
    
    def _extract_structured_data(self, text: str, doc_type: str) -> Dict:
        """Extrait des données structurées basées sur le type de document"""
        import re
        from datetime import datetime
        
        structured_data = {
            'entities': {},
            'personal_info': {},
            'financial_info': {},
            'dates': [],
            'amounts': [],
            'document_specific': {}
        }
        
        # Extraire les dates
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, text, re.IGNORECASE)
            structured_data['dates'].extend(dates)
        
        # Extraire les montants d'argent
        amount_patterns = [
            r'\d+[.,]\d{2}\s*€',
            r'\$\s*\d+[.,]\d{2}',
            r'\d+[.,]\d{2}\s*(euros|euro|EUR)',
            r'total\s*:?\s*(\d+[.,]\d{2})'
        ]
        
        for pattern in amount_patterns:
            amounts = re.findall(pattern, text, re.IGNORECASE)
            structured_data['amounts'].extend(amounts)
        
        # Extraire les emails
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            structured_data['entities']['emails'] = emails
        
        # Extraire les numéros de téléphone
        phones = re.findall(r'[\+\(]?[0-9][0-9\-\.\(\)]{8,}[0-9]', text)
        if phones:
            structured_data['entities']['phones'] = phones
        
        # Extraire les URLs
        urls = re.findall(r'https?://[^\s]+|www\.[^\s]+', text)
        if urls:
            structured_data['entities']['urls'] = urls
        
        # Données spécifiques au type de document
        if doc_type == 'facture':
            # Extraire numéro de facture
            invoice_nums = re.findall(r'facture\s*(?:n°|no)?\s*[:]?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
            if invoice_nums:
                structured_data['document_specific']['invoice_number'] = invoice_nums[0]
        
        elif doc_type == 'carte_identite' or doc_type == 'passeport':
            # Extraire noms
            name_pattern = r'(?:nom|name)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            names = re.findall(name_pattern, text, re.IGNORECASE)
            if names:
                structured_data['personal_info']['nom'] = names[0]
        
        return structured_data
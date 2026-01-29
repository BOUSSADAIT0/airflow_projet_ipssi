import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdf2image
import io
import os
import re
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class AdvancedOCRProcessor:
    def __init__(self, tesseract_path: str = None, default_language: str = "fra+eng"):
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.default_language = default_language
        
        # Modèles de détection pour différents types de documents
        self.document_patterns = {
            'invoice': {
                'keywords': ['facture', 'invoice', 'bill', 'montant', 'total', '€', '$', 'tv.a', 'tva', 'client'],
                'patterns': [
                    r'facture\s*[nN]°?\s*[\w-]+',
                    r'invoice\s*no\.?\s*[\w-]+',
                    r'total\s*[\d,.]+',
                    r'montant\s*[\d,.]+'
                ]
            },
            'receipt': {
                'keywords': ['reçu', 'receipt', 'ticket', 'caisse', 'paiement', 'caissier', 'merci'],
                'patterns': [
                    r'reçu\s*[\w-]+',
                    r'ticket\s*[\w-]+',
                    r'caisse\s*[\w-]+'
                ]
            },
            'contract': {
                'keywords': ['contrat', 'contract', 'agreement', 'entre', 'parties', 'signature'],
                'patterns': [
                    r'contrat\s*d[^\w]*[\w\s]+',
                    r'contract\s*[\w-]+',
                    r'entre\s*[\w\s]+et\s*[\w\s]+'
                ]
            },
            'cv': {
                'keywords': ['cv', 'curriculum vitae', 'expérience', 'compétences', 'formation'],
                'patterns': [
                    r'curriculum\s*vitae',
                    r'c\.v\.',
                    r'expérience\s*professionnelle'
                ]
            },
            'form': {
                'keywords': ['formulaire', 'form', 'nom', 'prénom', 'date', 'adresse'],
                'patterns': [
                    r'formulaire\s*[\w-]+',
                    r'nom\s*:\s*[\w\s]+',
                    r'prénom\s*:\s*[\w\s]+'
                ]
            },
            'letter': {
                'keywords': ['lettre', 'letter', 'cher', 'madame', 'monsieur', 'objet'],
                'patterns': [
                    r'lettre\s*[\w-]+',
                    r'cher\s*[\w\s]+',
                    r'objet\s*:\s*[\w\s]+'
                ]
            }
        }
        
        # Patterns pour l'extraction de données
        self.data_patterns = {
            'name': [
                r'(?:nom|name)\s*[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'm\.?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'mme\.?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
            ],
            'first_name': [
                r'(?:prénom|first name|prenom)\s*[.:]\s*([A-Z][a-z]+)',
                r'prénom\s*:\s*([A-Z][a-z]+)'
            ],
            'last_name': [
                r'(?:nom de famille|last name)\s*[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            ],
            'email': [
                r'[\w\.-]+@[\w\.-]+\.\w+',
                r'email\s*[.:]\s*([\w\.-]+@[\w\.-]+\.\w+)',
                r'e-mail\s*[.:]\s*([\w\.-]+@[\w\.-]+\.\w+)'
            ],
            'phone': [
                r'(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
                r'téléphone\s*[.:]\s*([\d\s\-\+\(\)\.]+)',
                r'tel\.?\s*[.:]\s*([\d\s\-\+\(\)\.]+)',
                r'phone\s*[.:]\s*([\d\s\-\+\(\)\.]+)'
            ],
            'date': [
                r'\d{1,2}/\d{1,2}/\d{2,4}',
                r'\d{1,2}-\d{1,2}-\d{2,4}',
                r'\d{4}/\d{1,2}/\d{1,2}',
                r'\d{1,2}\s+[a-zA-Z]+\s+\d{4}',
                r'date\s*[.:]\s*([\d/\-\s]+)'
            ],
            'address': [
                r'\d+\s+[a-zA-Z\s]+(?:rue|avenue|boulevard|street|road|av\.|bd\.)\s+[\w\s]+',
                r'adresse\s*[.:]\s*([\w\s,]+)',
                r'address\s*[.:]\s*([\w\s,]+)'
            ],
            'amount': [
                r'total\s*[\$€]?\s*([\d,.]+)',
                r'montant\s*[\$€]?\s*([\d,.]+)',
                r'[\$€]\s*([\d,.]+)',
                r'([\d,]+\.?\d*)\s*[\$€]'
            ],
            'invoice_number': [
                r'facture\s*[nN]°?\s*([\w-]+)',
                r'invoice\s*no\.?\s*([\w-]+)',
                r'réf\.?\s*([\w-]+)',
                r'ref\.?\s*([\w-]+)'
            ]
        }
    
    def process_file(self, file_content: bytes, filename: str, language: str = None) -> Dict[str, Any]:
        """Traite un fichier avec OCR avancé"""
        try:
            # 1. Détection du type de fichier et conversion
            images = self._convert_to_images(file_content, filename)
            
            if not images:
                return self._create_error_response("Impossible de convertir le fichier en images")
            
            # 2. Traitement OCR de chaque page
            ocr_results = []
            all_text = ""
            
            for i, image in enumerate(images):
                # Prétraitement de l'image
                processed_image = self._preprocess_image(image)
                
                # OCR avec configuration optimisée
                page_text, page_data = self._extract_with_ocr(processed_image, language)
                
                ocr_results.append({
                    'page': i + 1,
                    'text': page_text,
                    'confidence': page_data.get('confidence', 0),
                    'word_count': len(page_text.split()),
                    'data': page_data
                })
                
                all_text += f"--- Page {i+1} ---\n{page_text}\n\n"
            
            # 3. Analyse du document complet
            document_type = self._detect_document_type(all_text, filename)
            extracted_data = self._extract_structured_data(all_text, document_type)
            
            # 4. Détection des zones clés
            zones = self._detect_key_zones(images[0] if images else None, all_text)
            
            return {
                'success': True,
                'filename': filename,
                'document_type': document_type,
                'total_pages': len(images),
                'text': all_text,
                'pages': ocr_results,
                'structured_data': extracted_data,
                'zones': zones,
                'average_confidence': sum(r['confidence'] for r in ocr_results) / len(ocr_results) if ocr_results else 0,
                'metadata': {
                    'processing_date': datetime.now().isoformat(),
                    'language': language or self.default_language,
                    'file_size': len(file_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur OCR avancé: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))
    
    def _convert_to_images(self, content: bytes, filename: str) -> List[Image.Image]:
        """Convertit le fichier en liste d'images"""
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            if file_ext == '.pdf':
                # Convertir PDF en images
                return pdf2image.convert_from_bytes(
                    content,
                    dpi=300,
                    fmt='jpeg',
                    thread_count=2
                )
            else:
                # Pour les images
                image = Image.open(io.BytesIO(content))
                # Convertir en RGB si nécessaire
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                return [image]
                
        except Exception as e:
            logger.error(f"Erreur conversion: {str(e)}")
            return []
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Prétraite l'image pour améliorer l'OCR"""
        try:
            # Convertir en numpy array pour OpenCV
            img_array = np.array(image)
            
            # Convertir en niveaux de gris
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Désaturation pour améliorer le contraste
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            
            # Réduction du bruit
            gray = cv2.medianBlur(gray, 3)
            
            # Seuillage adaptatif
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Amélioration des bords
            kernel = np.ones((1, 1), np.uint8)
            gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # Retourner à PIL Image
            return Image.fromarray(gray)
            
        except Exception as e:
            logger.error(f"Erreur prétraitement: {str(e)}")
            return image
    
    def _extract_with_ocr(self, image: Image.Image, language: str = None) -> Tuple[str, Dict]:
        """Extrait le texte avec Tesseract et données détaillées"""
        try:
            # Configuration Tesseract optimisée
            config = '--oem 3 --psm 3 -c preserve_interword_spaces=1'
            
            # Extraction du texte
            text = pytesseract.image_to_string(
                image,
                lang=language or self.default_language,
                config=config
            )
            
            # Données détaillées pour la confiance
            data = pytesseract.image_to_data(
                image,
                lang=language or self.default_language,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calcul de la confiance moyenne
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0
            
            # Détection de la mise en page
            layout_data = self._analyze_layout(data)
            
            return text, {
                'confidence': avg_confidence,
                'word_count': len([w for w in data['text'] if w.strip()]),
                'layout': layout_data
            }
            
        except Exception as e:
            logger.error(f"Erreur extraction OCR: {str(e)}")
            return "", {'confidence': 0, 'error': str(e)}
    
    def _analyze_layout(self, ocr_data: Dict) -> Dict:
        """Analyse la mise en page du document"""
        try:
            blocks = {}
            current_block = None
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                if not text:
                    continue
                
                # Regrouper par position verticale
                top = ocr_data['top'][i]
                if current_block is None or abs(top - current_block['top']) > 20:
                    current_block = {
                        'text': text,
                        'top': top,
                        'left': ocr_data['left'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i]
                    }
                    blocks[top] = current_block
                else:
                    current_block['text'] += ' ' + text
            
            return {
                'block_count': len(blocks),
                'blocks': list(blocks.values())[:10]  # Limiter aux 10 premiers blocs
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse layout: {str(e)}")
            return {'block_count': 0, 'blocks': []}
    
    def _detect_document_type(self, text: str, filename: str) -> str:
        """Détecte le type de document"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        scores = {}
        
        for doc_type, patterns in self.document_patterns.items():
            score = 0
            
            # Points pour les mots-clés
            for keyword in patterns['keywords']:
                if keyword in text_lower or keyword in filename_lower:
                    score += 2
            
            # Points pour les patterns regex
            for pattern in patterns['patterns']:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 3
            
            scores[doc_type] = score
        
        # Retourner le type avec le score le plus élevé
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                return best_type[0]
        
        return 'document'
    
    def _extract_structured_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Extrait les données structurées selon le type de document"""
        extracted = {
            'document_type': doc_type,
            'entities': {},
            'raw_matches': {}
        }
        
        # Extraire toutes les données possibles
        for field, patterns in self.data_patterns.items():
            matches = []
            for pattern in patterns:
                try:
                    found = re.findall(pattern, text, re.IGNORECASE)
                    if found:
                        matches.extend([m if isinstance(m, str) else m[0] for m in found if m])
                except:
                    continue
            
            if matches:
                # Nettoyer et dédupliquer
                clean_matches = list(set([
                    m.strip().replace('\n', ' ').replace('\r', ' ')
                    for m in matches if m and len(str(m).strip()) > 1
                ]))
                
                if clean_matches:
                    extracted['entities'][field] = clean_matches
                    extracted['raw_matches'][field] = clean_matches
        
        # Traitement spécifique par type de document
        if doc_type == 'invoice':
            extracted.update(self._extract_invoice_data(text))
        elif doc_type == 'cv':
            extracted.update(self._extract_cv_data(text))
        elif doc_type == 'contract':
            extracted.update(self._extract_contract_data(text))
        
        # Extraire les informations personnelles
        personal_info = self._extract_personal_info(text)
        extracted['personal_info'] = personal_info
        
        # Statistiques
        extracted['stats'] = {
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'entity_count': len(extracted['entities']),
            'match_count': sum(len(v) for v in extracted['entities'].values())
        }
        
        return extracted
    
    def _extract_personal_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations personnelles"""
        info = {
            'full_name': None,
            'first_name': None,
            'last_name': None,
            'email': None,
            'phone': None,
            'address': None
        }
        
        # Nom complet (pattern le plus probable)
        name_patterns = [
            r'(?:nom complet|full name)\s*[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'm\.\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'mme\.\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?=\n|$)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1) if match.groups() else match.group(0)
                if name and len(name.split()) >= 2:
                    info['full_name'] = name.strip()
                    
                    # Séparer prénom/nom
                    parts = name.split()
                    info['first_name'] = parts[0]
                    info['last_name'] = ' '.join(parts[1:])
                    break
        
        # Email
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if emails:
            info['email'] = emails[0]
        
        # Téléphone
        phone_patterns = [
            r'(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
            r'tel[\.:]?\s*([\d\s\-\+\(\)]{8,})'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = phones[0] if isinstance(phones[0], str) else phones[0][0]
                info['phone'] = phone.strip()
                break
        
        # Adresse
        address_patterns = [
            r'adresse\s*[.:]\s*([^\n]{10,50})',
            r'(\d+\s+[a-zA-Z\s]+(?:rue|avenue|boulevard)[^\n]{5,40})'
        ]
        
        for pattern in address_patterns:
            addresses = re.findall(pattern, text, re.IGNORECASE)
            if addresses:
                info['address'] = addresses[0].strip()
                break
        
        return info
    
    def _extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """Extrait les données spécifiques aux factures"""
        invoice_data = {}
        
        # Numéro de facture
        inv_patterns = [
            r'facture\s*[nN]°?\s*([A-Z0-9-]+)',
            r'invoice\s*no\.?\s*([A-Z0-9-]+)',
            r'réf(?:érence)?\.?\s*([A-Z0-9-]+)'
        ]
        
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['invoice_number'] = match.group(1)
                break
        
        # Dates
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}/\d{1,2}/\d{1,2}', text)
        if dates:
            invoice_data['dates'] = dates
            invoice_data['invoice_date'] = dates[0] if len(dates) > 0 else None
            invoice_data['due_date'] = dates[1] if len(dates) > 1 else None
        
        # Montants
        amount_patterns = [
            r'total\s*[\$€]?\s*([\d,.]+)',
            r'montant\s*[\$€]?\s*([\d,.]+)',
            r'sous-total\s*[\$€]?\s*([\d,.]+)',
            r'tva\s*[\$€]?\s*([\d,.]+)'
        ]
        
        amounts = {}
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                key = pattern.split()[0].replace('-', '_')
                amounts[key] = matches[0] if isinstance(matches[0], str) else matches[0][0]
        
        if amounts:
            invoice_data['amounts'] = amounts
        
        # Client/Fournisseur
        client_patterns = [
            r'client\s*[.:]\s*([^\n]{5,50})',
            r'fournisseur\s*[.:]\s*([^\n]{5,50})',
            r'à\s+l\'attention\s*de\s*([^\n]{5,50})'
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['client'] = match.group(1).strip()
                break
        
        return {'invoice_info': invoice_data}
    
    def _extract_cv_data(self, text: str) -> Dict[str, Any]:
        """Extrait les données spécifiques aux CV"""
        cv_data = {}
        
        # Compétences
        skill_patterns = [
            r'compétences\s*[.:]\s*([^\n]{10,200})',
            r'skills\s*[.:]\s*([^\n]{10,200})',
            r'(?:java|python|javascript|react|angular|vue|sql|nosql)\s*(?:\n|,)'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                skills.extend([m.strip() for m in matches if m])
        
        if skills:
            cv_data['skills'] = list(set(skills))[:20]  # Limiter à 20
        
        # Expérience
        exp_pattern = r'expérience\s*[.:]\s*([^\n]{10,500})'
        match = re.search(exp_pattern, text, re.IGNORECASE)
        if match:
            cv_data['experience_summary'] = match.group(1).strip()
        
        # Formation
        edu_pattern = r'formation\s*[.:]\s*([^\n]{10,300})'
        match = re.search(edu_pattern, text, re.IGNORECASE)
        if match:
            cv_data['education'] = match.group(1).strip()
        
        return {'cv_info': cv_data}
    
    def _extract_contract_data(self, text: str) -> Dict[str, Any]:
        """Extrait les données spécifiques aux contrats"""
        contract_data = {}
        
        # Parties
        party_patterns = [
            r'entre\s*([^\n]{10,100})\s*et\s*([^\n]{10,100})',
            r'parties\s*[.:]\s*\n*(1\..*?)\n*(2\..*?)(?:\n|$)'
        ]
        
        for pattern in party_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if len(match.groups()) >= 2:
                    contract_data['party_a'] = match.group(1).strip()
                    contract_data['party_b'] = match.group(2).strip()
                    break
        
        # Date de signature
        sig_patterns = [
            r'fait\s*à\s*[\w\s]+\s*le\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'signé\s*le\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'date\s*de\s*signature\s*[.:]\s*(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in sig_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                contract_data['signature_date'] = match.group(1)
                break
        
        # Durée
        duration_pattern = r'durée\s*[.:]\s*([^\n]{5,50})'
        match = re.search(duration_pattern, text, re.IGNORECASE)
        if match:
            contract_data['duration'] = match.group(1).strip()
        
        return {'contract_info': contract_data}
    
    def _detect_key_zones(self, image: Optional[Image.Image], text: str) -> List[Dict]:
        """Détecte les zones clés dans le document"""
        zones = []
        
        if not image:
            return zones
        
        try:
            # Détection basée sur le texte
            important_keywords = [
                'nom', 'prénom', 'date', 'adresse', 'email', 'téléphone',
                'montant', 'total', 'facture', 'client', 'signature'
            ]
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line_lower = line.lower()
                for keyword in important_keywords:
                    if keyword in line_lower:
                        zones.append({
                            'type': keyword,
                            'text': line.strip(),
                            'line_number': i + 1,
                            'confidence': 0.8
                        })
                        break
            
            # Limiter le nombre de zones
            return zones[:20]
            
        except Exception as e:
            logger.error(f"Erreur détection zones: {str(e)}")
            return []
    
    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Crée une réponse d'erreur standardisée"""
        return {
            'success': False,
            'error': error_msg,
            'filename': '',
            'document_type': 'unknown',
            'total_pages': 0,
            'text': '',
            'pages': [],
            'structured_data': {},
            'zones': [],
            'average_confidence': 0,
            'metadata': {
                'processing_date': datetime.now().isoformat(),
                'error': error_msg
            }
        }
"""
Service de traitement des factures 
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logger
logging.basicConfig(level=logging.INFO)
app_logger = logging.getLogger(__name__)

# Configuration par défaut
CLIENT_SIRET = os.environ.get('CLIENT_SIRET', '')
EXCEL_AVAILABLE = True
PDF2IMAGE_AVAILABLE = False

class WebUICallbacks:
    """Callbacks pour l'interface web (remplace TkinterUICallbacks)"""
    def __init__(self):
        self.progress_data = {}
        self.status_messages = []
    
    def update_progress(self, value, max_value=100, message=""):
        """Met à jour la progression"""
        self.progress_data = {
            'value': value,
            'max_value': max_value,
            'percent': int((value / max_value * 100)) if max_value > 0 else 0,
            'message': message
        }
        app_logger.info(f"Progression: {value}/{max_value} - {message}")
    
    def update_status(self, message, status_type="info"):
        """Met à jour le statut"""
        self.status_messages.append({
            'message': message,
            'type': status_type,
            'timestamp': datetime.now().isoformat()
        })
        app_logger.info(f"Status [{status_type}]: {message}")
    
    def display_extracted_data(self, data):
        """Affiche les données extraites"""
        self.extracted_data = data

class InvoiceProcessor:
    """Processeur de factures pour l'interface web et Airflow - Version simplifiée"""
    
    def __init__(self, excel_file_path=None, client_siret=None):
        self.excel_file_path = excel_file_path or os.path.join('data', 'factures.xlsx')
        self.client_siret = client_siret or CLIENT_SIRET
        
        # Initialiser OpenAI et Ollama
        self.openai_available = self._init_openai()
        self.ollama_available, self.ollama_models, self.ollama_base_url = self._init_ollama()
        
        # Créer les callbacks web
        self.callbacks = WebUICallbacks()
        
        app_logger.info(f"InvoiceProcessor initialisé - OpenAI: {self.openai_available}, Ollama: {self.ollama_available}")
    
    def _init_openai(self):
        """Initialise OpenAI"""
        return bool(os.environ.get('OPENAI_API_KEY'))
    
    def _init_ollama(self):
        """Initialise Ollama"""
        try:
            import requests
            base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            # Vérifier si Ollama est disponible
            try:
                response = requests.get(f"{base_url}/api/tags", timeout=2)
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [m.get('name', '') for m in models_data.get('models', [])]
                    
                    # Prioriser certains modèles
                    preferred_models = ["llama3.2", "mistral", "deepseek-coder"]
                    models = []
                    
                    for preferred in preferred_models:
                        for model in available_models:
                            if preferred.lower() in model.lower():
                                if model not in models:
                                    models.append(model)
                                    break
                    
                    if not models and available_models:
                        models = available_models[:3]
                    
                    app_logger.info(f"Ollama disponible avec modèles: {models}")
                    return True, models, base_url
            except Exception as e:
                app_logger.warning(f"Ollama non disponible: {e}")
            
            return False, [], base_url
        except ImportError:
            app_logger.warning("Bibliothèque requests non disponible pour Ollama")
            return False, [], "http://localhost:11434"
    
    def process_invoice(self, filepath, method='auto'):
        """
        Traite une facture et retourne les données extraites
        
        Args:
            filepath: Chemin vers le fichier (PDF ou image)
            method: Méthode d'extraction ('ollama', 'tesseract', 'auto')
        
        Returns:
            dict: Résultat avec 'success', 'data', 'error'
        """
        if not os.path.exists(filepath):
            return {
                'success': False,
                'error': f'Fichier introuvable: {filepath}'
            }
        
        try:
            self.callbacks.update_progress(10, 100, "Lecture du fichier...")
            
            # Détecter le type de fichier
            file_ext = os.path.splitext(filepath)[1].lower()
            
            # Si c'est un PDF, essayer de le convertir en image
            if file_ext == '.pdf':
                self.callbacks.update_progress(20, 100, "Conversion PDF en image...")
                image_path = self._convert_pdf_to_image(filepath)
                if not image_path:
                    return {
                        'success': False,
                        'error': 'Impossible de convertir le PDF en image'
                    }
                filepath = image_path
            
            # Extraire le texte avec la méthode choisie
            self.callbacks.update_progress(40, 100, f"Extraction avec {method}...")
            extracted_text = self._extract_text(filepath, method)
            
            if not extracted_text:
                return {
                    'success': False,
                    'error': 'Aucun texte extrait du fichier'
                }
            
            # Parser les données depuis le texte
            self.callbacks.update_progress(70, 100, "Analyse des données...")
            extracted_data = self._parse_invoice_data(extracted_text)
            
            # Enrichir avec SIRET si possible
            self.callbacks.update_progress(90, 100, "Enrichissement des données...")
            if not extracted_data.get('siret'):
                extracted_data = self._enrich_with_siret(extracted_data)
            
            self.callbacks.update_progress(100, 100, "Terminé!")
            
            return {
                'success': True,
                'data': extracted_data,
                'filepath': filepath,
                'method_used': method
            }
        
        except Exception as e:
            app_logger.error(f"Erreur lors du traitement de {filepath}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _convert_pdf_to_image(self, pdf_path):
        """Convertit un PDF en image"""
        try:
            # Essayer pdf2image d'abord
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(pdf_path, first_page=1, last_page=1)
                if images:
                    image_path = pdf_path.replace('.pdf', '_page1.png')
                    images[0].save(image_path, 'PNG')
                    return image_path
            except ImportError:
                pass
            
            # Fallback: utiliser PyMuPDF (fitz)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                page = doc[0]
                pix = page.get_pixmap()
                image_path = pdf_path.replace('.pdf', '_page1.png')
                pix.save(image_path)
                doc.close()
                return image_path
            except ImportError:
                pass
            
            app_logger.warning("Aucune bibliothèque PDF disponible (pdf2image ou PyMuPDF)")
            return None
        except Exception as e:
            app_logger.error(f"Erreur lors de la conversion PDF: {e}")
            return None
    
    def _extract_text(self, filepath, method='auto'):
        """Extrait le texte d'une image"""
        try:
            # Si méthode auto, essayer Ollama puis Tesseract
            if method == 'auto':
                if self.ollama_available:
                    method = 'ollama'
                else:
                    method = 'tesseract'
            
            if method == 'ollama' and self.ollama_available:
                return self._extract_with_ollama(filepath)
            elif method == 'tesseract':
                return self._extract_with_tesseract(filepath)
            else:
                # Fallback sur Tesseract
                return self._extract_with_tesseract(filepath)
        except Exception as e:
            app_logger.error(f"Erreur lors de l'extraction: {e}")
            return None
    
    def _extract_with_ollama(self, image_path):
        """Extrait le texte avec Ollama"""
        try:
            import requests
            import base64
            
            # Lire l'image et la convertir en base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Utiliser le premier modèle disponible
            model = self.ollama_models[0] if self.ollama_models else "llama3.2"
            
            # Appel à Ollama pour extraction OCR
            prompt = """Extrait toutes les informations textuelles de cette image de facture. 
            Retourne uniquement le texte brut, sans formatage."""
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                app_logger.warning(f"Ollama a retourné une erreur: {response.status_code}")
                return None
        except Exception as e:
            app_logger.error(f"Erreur avec Ollama: {e}")
            return None
    
    def _extract_with_tesseract(self, image_path):
        """Extrait le texte avec Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            # Tesseract path (peut être configuré)
            tesseract_path = os.environ.get('TESSERACT_PATH', 'tesseract')
            if tesseract_path and os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='fra+eng')
            return text
        except ImportError:
            app_logger.error("pytesseract non installé. Installez avec: pip install pytesseract")
            return None
        except Exception as e:
            app_logger.error(f"Erreur avec Tesseract: {e}")
            return None
    
    def _parse_invoice_data(self, text):
        """Parse les données de facture depuis le texte extrait"""
        import re
        
        data = {
            "date": "",
            "numero_facture": "",
            "fournisseur": "",
            "total_ht": "",
            "total_ttc": "",
            "tva": "",
            "siret": "",
            "siren": "",
            "adresse_fournisseur": "",
            "code_postal": "",
            "ville": ""
        }
        
        if not text:
            return data
        
        # Extraire la date (format JJ/MM/AAAA ou DD/MM/YYYY)
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
        dates = re.findall(date_pattern, text)
        if dates:
            data["date"] = dates[0]
        
        # Extraire le numéro de facture
        facture_pattern = r'(?:facture|invoice|n[°o]|num[ée]ro)[\s:]*([A-Z0-9\-]+)'
        facture_match = re.search(facture_pattern, text, re.IGNORECASE)
        if facture_match:
            data["numero_facture"] = facture_match.group(1)
        
        # Extraire les montants
        montant_pattern = r'(?:total|montant|amount)[\s:]*([\d\s,\.]+)'
        montants = re.findall(montant_pattern, text, re.IGNORECASE)
        if montants:
            try:
                montant = float(montants[-1].replace(',', '.').replace(' ', ''))
                data["total_ttc"] = montant
            except:
                pass
        
        # Extraire SIRET (14 chiffres)
        siret_pattern = r'\b(\d{14})\b'
        siret_match = re.search(siret_pattern, text)
        if siret_match:
            siret = siret_match.group(1)
            data["siret"] = siret
            data["siren"] = siret[:9]  # SIREN = 9 premiers chiffres
        
        # Extraire le code postal (5 chiffres)
        cp_pattern = r'\b(\d{5})\b'
        cp_match = re.search(cp_pattern, text)
        if cp_match:
            data["code_postal"] = cp_match.group(1)
        
        return data
    
    def _enrich_with_siret(self, data):
        """Enrichit les données avec SIRET via API"""
        # Cette fonction peut être implémentée plus tard avec une vraie API
        return data
    
    def export_to_excel(self, invoice_data, excel_path=None):
        """Exporte les données vers Excel"""
        if not EXCEL_AVAILABLE:
            try:
                import openpyxl
            except ImportError:
                return {
                    'success': False,
                    'error': 'Excel non disponible (openpyxl non installé)'
                }
        
        excel_path = excel_path or self.excel_file_path
        
        try:
            from openpyxl import Workbook, load_workbook
            from openpyxl.styles import Font, PatternFill
            from openpyxl.styles.numbers import FORMAT_NUMBER_00
            from openpyxl.utils import get_column_letter
            
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(excel_path), exist_ok=True)
            
            # Charger ou créer le fichier
            if os.path.exists(excel_path):
                wb = load_workbook(excel_path)
                ws = wb.active
            else:
                wb = Workbook()
                ws = wb.active
                ws.title = "Factures"
                
                # Créer les en-têtes
                headers = ["Date Facture", "Numéro Facture", "Fournisseur", "SIREN", "SIRET",
                          "Adresse", "Code Postal", "Ville", "ID Client", 
                          "Total HT", "TVA", "Total TTC", "Fichier PDF", "Date Extraction"]
                ws.append(headers)
                
                # Formater les en-têtes
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
            
            # Préparer les données
            row_data = [
                invoice_data.get("date", ""),
                invoice_data.get("numero_facture", ""),
                invoice_data.get("fournisseur", ""),
                invoice_data.get("siren", ""),
                invoice_data.get("siret", ""),
                invoice_data.get("adresse_fournisseur", ""),
                invoice_data.get("code_postal", ""),
                invoice_data.get("ville", ""),
                invoice_data.get("id_client", ""),
                invoice_data.get("total_ht", ""),
                invoice_data.get("tva", ""),
                invoice_data.get("total_ttc", ""),
                invoice_data.get("fichier_pdf", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            
            ws.append(row_data)
            
            # Formater les colonnes numériques
            last_row = ws.max_row
            for col_letter in ['J', 'K', 'L']:  # Total HT, TVA, Total TTC
                cell = ws[f"{col_letter}{last_row}"]
                if cell.value:
                    try:
                        cell.value = float(cell.value)
                        cell.number_format = FORMAT_NUMBER_00
                    except:
                        pass
            
            # Sauvegarder
            wb.save(excel_path)
            
            return {
                'success': True,
                'filepath': excel_path,
                'message': 'Données exportées avec succès'
            }
        
        except Exception as e:
            app_logger.error(f"Erreur lors de l'export Excel: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

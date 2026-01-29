import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import spacy
from dataclasses import dataclass
import json

@dataclass
class ExtractedField:
    """Champ sémantique extrait"""
    name: str
    value: Any
    confidence: float
    source_text: str
    position: Tuple[int, int, int, int]  # x, y, w, h

class SemanticExtractor:
    """Extracteur sémantique pour identifier les champs utiles"""
    
    def __init__(self):
        # Modèles de regex pour différents types de documents
        self.patterns = {
            'invoice': {
                'invoice_number': [
                    r'(?:facture|invoice|n°|numéro|no)\s*[:\.]?\s*([A-Z0-9\-]+)',
                    r'\b(?:FACT|INV|BLL)-?(\d{4,10})\b'
                ],
                'date': [
                    r'(?:date|échéance|du)\s*[:\.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                    r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b'
                ],
                # Nom du client
                'client_name': [
                    r'(?:client|destinataire|facturé à|à l\'attention de)\s*[:\.]?\s*([A-Za-zÀ-ÿ0-9\s\-&\.\'\,]+?)(?=\n|$|€|TVA|HT|TTC)',
                    r'(?:nom du client|client)\s*[:\.]?\s*([A-Za-zÀ-ÿ0-9\s\-&\.\'\,]+)',
                ],
                # Nom du fournisseur / émetteur
                'supplier_name': [
                    r'(?:fournisseur|émetteur|vendeur|facturé par|société)\s*[:\.]?\s*([A-Za-zÀ-ÿ0-9\s\-&\.\'\,]+?)(?=\n|$|SIRET|N°|client)',
                    r'(?:raison sociale|entreprise)\s*[:\.]?\s*([A-Za-zÀ-ÿ0-9\s\-&\.\'\,]+)',
                ],
                # Montant HT
                'amount_ht': [
                    r'(?:total\s+)?HT\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                    r'(?:montant\s+)?(?:total\s+)?HT\s*[:\.]?\s*([\d\s,\.]+)\s*[€$£]',
                    r'[\d\s,\.]+\s*[€$£]\s*HT\b.*?([\d\s,\.]+)\s*[€$£]',
                ],
                # TVA (montant ou taux)
                'vat_amount': [
                    r'(?:TVA|tva)\s*[:\.]?\s*([\d\s,\.]+\s*[€$£]|\d+(?:[.,]\d+)?\s*%)',
                    r'\b([\d\s,\.]+)\s*[€$£]\s*(?:TVA)\b',
                    r'(?:montant\s+)?TVA\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                ],
                # Montant TTC
                'amount_ttc': [
                    r'(?:total\s+)?TTC\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                    r'(?:montant\s+)?(?:total\s+)?TTC\s*[:\.]?\s*([\d\s,\.]+)\s*[€$£]',
                    r'(?:à payer|total à payer|net à payer)\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                ],
                'total_amount': [
                    r'(?:total|montant|à payer|TOTAL)\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                    r'\b([\d\s,\.]+)\s*[€$£]\s*(?:TTC|HT)?\b'
                ],
            },
            'cv': {
                'name': [
                    r'^(?:M\.|Mme|Mr|Ms|Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b',
                    r'\b(?:Nom|Name)\s*[:\.]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
                ],
                'email': [
                    r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b'
                ],
                'phone': [
                    r'\b(?:\+33|0)[1-9](?:[\s\.]?\d{2}){4}\b',
                    r'\b\d{2}[\s\.]?\d{2}[\s\.]?\d{2}[\s\.]?\d{2}[\s\.]?\d{2}\b'
                ],
                'skills': [
                    r'\b(?:Python|Java|JavaScript|React|Angular|Vue|Django|Flask|FastAPI|SQL|NoSQL|MongoDB|PostgreSQL|Docker|Kubernetes|AWS|Azure|Git)\b'
                ]
            },
            'generic': {
                'date': [
                    r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
                    r'\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b'
                ],
                'amount': [
                    r'\b[\d\s,\.]+\s*[€$£]\b'
                ],
                'percentage': [
                    r'\b\d+%\b'
                ],
                'email': [
                    r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b'
                ],
                'url': [
                    r'\bhttps?://[\w\.-]+\.[a-z]{2,}(?:/[\w\.-]*)*\b'
                ]
            }
        }
        
        # Chargement du modèle spaCy pour le français
        try:
            self.nlp = spacy.load("fr_core_news_sm")
        except:
            self.nlp = None
    
    def extract_from_text(self, text: str, doc_type: str = "generic") -> List[ExtractedField]:
        """Extrait les champs sémantiques d'un texte"""
        fields = []
        
        # Sélection des patterns en fonction du type de document
        patterns = self.patterns.get(doc_type, {})
        if doc_type != "generic":
            patterns.update(self.patterns['generic'])
        
        for field_name, regex_list in patterns.items():
            for pattern in regex_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.groups() else match.group()
                    
                    # Calcul de la confiance basée sur la précision du pattern
                    confidence = self._calculate_confidence(field_name, pattern, value)
                    
                    field = ExtractedField(
                        name=field_name,
                        value=value,
                        confidence=confidence,
                        source_text=match.group(),
                        position=(0, 0, 0, 0)  # À adapter si on a les coordonnées
                    )
                    fields.append(field)
        
        return fields
    
    def _calculate_confidence(self, field_name: str, pattern: str, value: str) -> float:
        """Calcule la confiance d'extraction d'un champ"""
        confidence = 0.7  # Valeur par défaut
        
        # Ajustements basés sur le type de champ
        if field_name == 'email':
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', value):
                confidence = 0.95
        
        elif field_name == 'date':
            try:
                # Tentative de parsing de la date
                date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', 
                               '%Y/%m/%d', '%Y-%m-%d', '%Y.%m.%d',
                               '%d %B %Y', '%B %d, %Y']
                
                for fmt in date_formats:
                    try:
                        datetime.strptime(value, fmt)
                        confidence = 0.9
                        break
                    except:
                        continue
            except:
                confidence = 0.6
        
        elif field_name == 'amount':
            # Vérification du format monétaire
            if re.match(r'^[\d\s,\.]+\s*[€$£]$', value):
                confidence = 0.85
        
        elif field_name == 'phone':
            # Nettoyage du numéro
            clean_number = re.sub(r'[\s\.\-]', '', value)
            if re.match(r'^(?:\+33|0)[1-9]\d{8}$', clean_number):
                confidence = 0.9

        elif field_name in ('amount_ht', 'amount_ttc', 'total_amount', 'vat_amount'):
            # Montants facture
            if re.match(r'^[\d\s,\.]+\s*[€$£]$', value.strip()) or re.match(r'^\d+(?:[.,]\d+)?\s*%$', value.strip()):
                confidence = 0.88

        elif field_name == 'client_name':
            # Nom client : texte non vide, pas uniquement des chiffres
            clean = value.strip()
            if len(clean) > 2 and not re.match(r'^[\d\s,\.€$£]+$', clean):
                confidence = 0.82

        elif field_name == 'supplier_name':
            # Nom fournisseur
            clean = value.strip()
            if len(clean) > 2 and not re.match(r'^[\d\s,\.€$£]+$', clean):
                confidence = 0.82
        
        return confidence
    
    def extract_entities_spacy(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités nommées avec spaCy"""
        if not self.nlp:
            return {}
        
        doc = self.nlp(text)
        entities = {}
        
        for ent in doc.ents:
            label = ent.label_
            if label not in entities:
                entities[label] = []
            entities[label].append(ent.text)
        
        return entities
    
    def detect_document_type(self, text: str) -> str:
        """Détecte le type de document basé sur le contenu"""
        text_lower = text.lower()
        
        # Mots-clés pour différents types de documents
        keywords = {
            'invoice': ['facture', 'invoice', 'montant', 'total', 'tva', 'client', 'paiement'],
            'cv': ['curriculum', 'vitae', 'expérience', 'compétence', 'formation', 'diplôme'],
            'contract': ['contrat', 'article', 'clause', 'signature', 'parties', 'engagement'],
            'form': ['formulaire', 'nom', 'prénom', 'adresse', 'date de naissance', 'signature']
        }
        
        scores = {}
        for doc_type, words in keywords.items():
            score = sum(1 for word in words if word in text_lower)
            if score > 0:
                scores[doc_type] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'generic'
    
    def structure_data(self, text: str, zones: List[Any] = None) -> Dict[str, Any]:
        """Structure les données extraites"""
        doc_type = self.detect_document_type(text)
        fields = self.extract_from_text(text, doc_type)
        
        # Regroupement par type de champ
        structured = {
            'document_type': doc_type,
            'extraction_date': datetime.now().isoformat(),
            'fields': {},
            'raw_text': text
        }
        
        for field in fields:
            if field.name not in structured['fields']:
                structured['fields'][field.name] = []
            
            structured['fields'][field.name].append({
                'value': field.value,
                'confidence': field.confidence,
                'source': field.source_text
            })
        
        # Extraction avec spaCy si disponible
        if self.nlp:
            entities = self.extract_entities_spacy(text)
            structured['named_entities'] = entities
        
        return structured
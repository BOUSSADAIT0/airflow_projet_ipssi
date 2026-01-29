"""
Extracteur sémantique pour identifier les champs utiles dans tout type de document.
Remplace les appels Ollama/API par une extraction locale (regex + spaCy optionnel).
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
import json

# spaCy optionnel (pas obligatoire pour faire tourner)
try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False
    spacy = None


@dataclass
class ExtractedField:
    """Champ sémantique extrait"""
    name: str
    value: Any
    confidence: float
    source_text: str
    position: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h


class SemanticExtractor:
    """
    Extracteur sémantique pour tout type de document.
    Utilise des regex + spaCy (si installé) — pas d'appel Ollama ni API externe.
    """

    def __init__(self):
        self.patterns = {
            'invoice': {
                'invoice_number': [
                    r'(?:facture|invoice|n°|numéro|no)\s*[:\.]?\s*([A-Z0-9\-]+)',
                    r'\b(?:FACT|INV|BLL)-?(\d{4,10})\b',
                ],
                'date': [
                    r'(?:date|échéance|du)\s*[:\.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                    r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b',
                ],
                'total_amount': [
                    r'(?:total|montant|à payer|TOTAL)\s*[:\.]?\s*([\d\s,\.]+\s*[€$£])',
                    r'\b([\d\s,\.]+)\s*[€$£]\s*(?:TTC|HT)?\b',
                ],
                'vat_amount': [
                    r'(?:TVA|tva)\s*[:\.]?\s*([\d\s,\.]+\s*[€$£]|\d+%)',
                    r'\b([\d\s,\.]+)\s*[€$£]\s*(?:TVA)\b',
                ],
                'siret': [
                    r'\b(\d{14})\b',
                    r'(?:siret|siren)\s*[:\.]?\s*([\d\s]{9,14})\b',
                ],
                'code_postal': [
                    r'\b(\d{5})\b',
                ],
            },
            'cv': {
                'name': [
                    r'^(?:M\.|Mme|Mr|Ms|Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b',
                    r'\b(?:Nom|Name)\s*[:\.]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                ],
                'email': [
                    r'\b([\w\.-]+@[\w\.-]+\.\w{2,})\b',
                ],
                'phone': [
                    r'\b((?:\+33|0)[1-9](?:[\s\.]?\d{2}){4})\b',
                    r'\b(\d{2}[\s\.]?\d{2}[\s\.]?\d{2}[\s\.]?\d{2}[\s\.]?\d{2})\b',
                ],
                'skills': [
                    r'\b(Python|Java|JavaScript|React|Angular|Vue|Django|Flask|FastAPI|SQL|NoSQL|MongoDB|PostgreSQL|Docker|Kubernetes|AWS|Azure|Git)\b',
                ],
            },
            'generic': {
                'date': [
                    r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
                    r'\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b',
                ],
                'amount': [
                    r'\b([\d\s,\.]+\s*[€$£])\b',
                ],
                'percentage': [
                    r'\b(\d+%)\b',
                ],
                'email': [
                    r'\b([\w\.-]+@[\w\.-]+\.\w{2,})\b',
                ],
                'url': [
                    r'\b(https?://[\w\.-]+\.[a-z]{2,}(?:/[\w\.-]*)*)\b',
                ],
            },
        }

        self.nlp = None
        if _SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("fr_core_news_sm")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except OSError:
                    pass

    def extract_from_text(self, text: str, doc_type: str = "generic") -> List[ExtractedField]:
        """Extrait les champs sémantiques d'un texte."""
        fields: List[ExtractedField] = []
        if not text or not text.strip():
            return fields

        # Fusion des patterns du type de document + generic
        patterns = dict(self.patterns.get('generic', {}))
        if doc_type and doc_type != 'generic':
            type_patterns = self.patterns.get(doc_type, {})
            for k, v in type_patterns.items():
                patterns[k] = patterns.get(k, []) + v

        for field_name, regex_list in patterns.items():
            for pattern in regex_list:
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        value = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                        if not value or not str(value).strip():
                            continue
                        confidence = self._calculate_confidence(field_name, pattern, value)
                        field = ExtractedField(
                            name=field_name,
                            value=value.strip(),
                            confidence=confidence,
                            source_text=match.group(0).strip(),
                            position=(0, 0, 0, 0),
                        )
                        fields.append(field)
                except re.error:
                    continue

        return fields

    def _calculate_confidence(self, field_name: str, pattern: str, value: str) -> float:
        """Calcule la confiance d'extraction d'un champ."""
        confidence = 0.7
        value = str(value).strip()

        if field_name == 'email':
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', value):
                confidence = 0.95
        elif field_name == 'date':
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']:
                try:
                    datetime.strptime(value.replace(' ', ''), fmt)
                    confidence = 0.9
                    break
                except ValueError:
                    continue
        elif field_name in ('amount', 'total_amount', 'vat_amount'):
            if re.search(r'[\d,\.]+\s*[€$£]', value):
                confidence = 0.85
        elif field_name == 'phone':
            clean = re.sub(r'[\s\.\-]', '', value)
            if re.match(r'^(?:\+33|0)[1-9]\d{8}$', clean):
                confidence = 0.9
        elif field_name == 'siret':
            digits = re.sub(r'\D', '', value)
            if len(digits) in (9, 14):
                confidence = 0.9
        elif field_name == 'invoice_number':
            confidence = 0.85

        return confidence

    def extract_entities_spacy(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités nommées avec spaCy si disponible."""
        if not self.nlp or not text:
            return {}
        try:
            doc = self.nlp(text[:100000])  # limiter la taille
            entities: Dict[str, List[str]] = {}
            for ent in doc.ents:
                if ent.label_ not in entities:
                    entities[ent.label_] = []
                if ent.text not in entities[ent.label_]:
                    entities[ent.label_].append(ent.text)
            return entities
        except Exception:
            return {}

    def detect_document_type(self, text: str) -> str:
        """Détecte le type de document à partir du contenu."""
        if not text:
            return 'generic'
        text_lower = text.lower()
        keywords = {
            'invoice': ['facture', 'invoice', 'montant', 'total', 'tva', 'client', 'paiement', 'siret', 'échéance'],
            'cv': ['curriculum', 'vitae', 'expérience', 'compétence', 'formation', 'diplôme', 'skills'],
            'contract': ['contrat', 'article', 'clause', 'signature', 'parties', 'engagement'],
            'form': ['formulaire', 'nom', 'prénom', 'adresse', 'date de naissance'],
        }
        scores = {}
        for doc_type, words in keywords.items():
            score = sum(1 for w in words if w in text_lower)
            if score > 0:
                scores[doc_type] = score
        if scores:
            return max(scores, key=scores.get)
        return 'generic'

    def structure_data(self, text: str, zones: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Structure les données extraites pour tout type de document.
        Pas d'appel API ni Ollama — 100 % local.
        """
        doc_type = self.detect_document_type(text)
        fields = self.extract_from_text(text, doc_type)

        structured: Dict[str, Any] = {
            'document_type': doc_type,
            'extraction_date': datetime.now().isoformat(),
            'fields': {},
            'raw_text': text[:5000] if len(text) > 5000 else text,
        }

        for f in fields:
            if f.name not in structured['fields']:
                structured['fields'][f.name] = []
            structured['fields'][f.name].append({
                'value': f.value,
                'confidence': f.confidence,
                'source': f.source_text,
            })

        if self.nlp:
            structured['named_entities'] = self.extract_entities_spacy(text)

        return structured

    def to_invoice_data(self, structured: Dict[str, Any]) -> Dict[str, str]:
        """
        Convertit la sortie structure_data en format attendu par export_to_excel
        (facture) : date, numero_facture, total_ttc, tva, siret, etc.
        """
        data = {
            'date': '',
            'numero_facture': '',
            'fournisseur': '',
            'total_ht': '',
            'total_ttc': '',
            'tva': '',
            'siret': '',
            'siren': '',
            'adresse_fournisseur': '',
            'code_postal': '',
            'ville': '',
            'document_type': structured.get('document_type', 'generic'),
        }
        fields = structured.get('fields', {})
        get_first = lambda name: (fields.get(name) or [{}])[0].get('value', '') if fields.get(name) else ''

        def _normalize_amount(s: str) -> str:
            """Retourne une chaîne numérique (virgule→point) pour Excel."""
            if not s:
                return ''
            s = re.sub(r'[€$£\s]', '', str(s).strip())
            s = s.replace(',', '.')
            parts = s.split('.')
            if len(parts) <= 1:
                return s
            # Format européen 1.234,56 → integer 1234, decimal 56
            return ''.join(parts[:-1]) + '.' + parts[-1]

        data['date'] = get_first('date') or get_first('invoice_date')
        data['numero_facture'] = get_first('invoice_number')
        data['total_ttc'] = _normalize_amount(get_first('total_amount') or get_first('amount'))
        data['tva'] = _normalize_amount(get_first('vat_amount'))
        data['siret'] = re.sub(r'\D', '', get_first('siret') or '')[:14]
        if data['siret']:
            data['siren'] = data['siret'][:9]
        data['code_postal'] = get_first('code_postal') or ''

        return data

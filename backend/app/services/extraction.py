import re
from typing import Dict, Any, List, Optional

def extract_email(text: str) -> Optional[str]:
    # Comprehensive email regex
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    return match.group(0) if match else None

def extract_phone(text: str) -> Optional[str]:
    # Supports international formats, French formats, etc.
    # Ex: +33 6 12 34 56 78, 06.12.34.56.78, (123) 456-7890
    patterns = [
        r'(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}', # French format
        r'\+?1?\s*\(?[-.\s]?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', # US/Generic
        r'(?:\+|00)\d{1,3}[\s.-]?\d{1,14}' # Generic International
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return None

def extract_name_candidate(text: str) -> Optional[str]:
    """
    Attempt to extract a name. This is hard without NER models like SpaCy.
    We'll look for lines that look like headers or start with typical labels.
    """
    lines = text.split('\n')
    # Heuristic: Name often on first non-empty line, capitalized
    for line in lines[:10]: # Check first 10 lines
        clean_line = line.strip()
        if not clean_line:
            continue
        # If line matches email or phone, skip
        if extract_email(clean_line) or extract_phone(clean_line):
           continue
        
        # Heuristic: 2 or 3 words, Title Case, no numbers
        if re.match(r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2}$', clean_line):
            return clean_line
            
    return None

def extract_cv_info(text: str) -> Dict[str, Any]:
    """Extract information specific to CVs in French and English."""
    result = {
        "type": "CV",
        "full_name": extract_name_candidate(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "address": None,
        "skills": [],
        "education": [],
        "experience": []
    }

    # Extended logic for sections
    sections = {
        "skills": ["Compétences", "Skills", "Expertise", "Langages", "Technologies"],
        "education": ["Formation", "Education", "Diplômes", "Academic", "Etudes"],
        "experience": ["Expérience", "Experience", "Parcours", "Employment", "Work History"]
    }
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Detect section headers
        is_header = False
        for section, keywords in sections.items():
            if any(key.lower() in line.lower() for key in keywords) and len(line) < 30:
                current_section = section
                is_header = True
                break
        
        if is_header: continue
        
        # Add content to section
        if current_section:
            if current_section == "skills":
                # Split by commas or bullets
                items = re.split(r'[,•\-|]', line)
                result["skills"].extend([i.strip() for i in items if i.strip()])
            else:
                result[current_section].append(line)
        
        # Address detection (simple)
        if not result["address"] and re.search(r'\d+\s+(?:Rue|Avenue|Boulevard|Street|Road|Lane|Impasse|Chemin)', line, re.IGNORECASE):
            result["address"] = line

    return result

def extract_invoice_info(text: str) -> Dict[str, Any]:
    """Extract information specific to Invoices."""
    result = {
        "type": "Invoice",
        "invoice_number": None,
        "date": None,
        "total_amount": None,
        "tax_amount": None,
        "vendor_name": None
    }
    
    # Invoice Number
    match_inv = re.search(r'(?:Facture|Invoice|Ref|N°)\s*[:#.]?\s*([A-Z0-9-/]+)', text, re.IGNORECASE)
    if match_inv:
        result["invoice_number"] = match_inv.group(1)
        
    # Date
    match_date = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if match_date:
        result["date"] = match_date.group(1)
        
    # Amounts (Total, TVA)
    # Looking for amounts with currency symbols
    amounts = re.findall(r'(\d+[.,]\d{2})\s*(?:€|\$|EUR|USD)', text)
    if amounts:
        # Heuristic: Max amount is usually Total
        try:
            amounts_float = [float(a.replace(',', '.')) for a in amounts]
            result["total_amount"] = max(amounts_float)
            if len(amounts_float) > 1:
                result["tax_amount"] = min(amounts_float) # Dangerous heuristic but better than nothing
        except:
            pass
            
    # Try to find specific "Total" line if regex above failed or to confirm
    if not result["total_amount"]:
        match_total = re.search(r'(?:Total|Montant TTC|Grand Total)\s*[:=]?\s*(\d+[.,]\d{2})', text, re.IGNORECASE)
        if match_total:
            result["total_amount"] = match_total.group(1)

    return result

def extract_structured_data(text: str, doc_type: str) -> Dict[str, Any]:
    """Main entry point for structured extraction"""
    if doc_type == 'cv':
        return extract_cv_info(text)
    elif doc_type == 'invoice':
        return extract_invoice_info(text)
    else:
        # Default extraction
        return {
            "emails": [extract_email(text)],
            "phones": [extract_phone(text)]
        }

# test_ocr_quality.py
import cv2
import numpy as np
from PIL import Image, ImageFilter
import io
import base64
from app.utils.ocr_processor_enhanced import EnhancedOCRProcessor

def test_low_quality_image():
    """Test avec une image de basse qualité simulée"""
    print("Test 1: Image basse qualité simulée")
    
    # Créer une image de test basse qualité
    img = np.zeros((500, 800, 3), dtype=np.uint8)
    cv2.putText(img, "Facture n° F-2024-001", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Date: 15/01/2024", (50, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Total: 1500.00 €", (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Ajouter du bruit
    noise = np.random.normal(0, 50, img.shape).astype(np.uint8)
    img = cv2.add(img, noise)
    
    # Ajouter un flou
    img = cv2.GaussianBlur(img, (5, 5), 0)
    
    # Réduire la résolution
    img = cv2.resize(img, (400, 250), interpolation=cv2.INTER_LINEAR)
    
    # Convertir en bytes
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
    img_bytes = buffer.tobytes()
    
    # Traiter avec OCR amélioré
    processor = EnhancedOCRProcessor()
    result = processor.process_file(img_bytes, "test_low_quality.jpg", "fra+eng")
    
    print(f"Succès: {result['success']}")
    print(f"Confiance: {result['average_confidence']:.2%}")
    print(f"Texte extrait:\n{result['text'][:500]}...")
    print(f"Méthodes utilisées: {[p.get('method_used') for p in result.get('pages', [])]}")
    print("-" * 80)

def test_high_quality_image():
    """Test avec une image haute qualité"""
    print("\nTest 2: Image haute qualité")
    
    # Créer une image de test haute qualité
    img = np.ones((1000, 1400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "CONTRAT DE PRESTATION DE SERVICES", (100, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, "Entre les soussignés :", (100, 180), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Société ABC, représentée par Monsieur Jean Dupont", (120, 230), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "et", (120, 280), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "Société XYZ, représentée par Madame Marie Martin", (120, 330), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    _, buffer = cv2.imencode('.png', img)
    img_bytes = buffer.tobytes()
    
    processor = EnhancedOCRProcessor()
    result = processor.process_file(img_bytes, "test_high_quality.png", "fra+eng")
    
    print(f"Succès: {result['success']}")
    print(f"Confiance: {result['average_confidence']:.2%}")
    print(f"Type de document détecté: {result['document_type']}")
    print(f"Données structurées: {result.get('structured_data', {})}")
    print("-" * 80)

def test_blurred_image():
    """Test avec une image floue"""
    print("\nTest 3: Image floue")
    
    img = np.ones((600, 900, 3), dtype=np.uint8) * 255
    cv2.putText(img, "RELEVE BANCAIRE", (100, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.putText(img, "Compte: FR76 3000 1000 1234 5678 9101 112", (100, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "Solde au 31/12/2023: 2.450,75 €", (100, 250), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    
    # Ajouter un flou important
    img = cv2.GaussianBlur(img, (15, 15), 10)
    
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    img_bytes = buffer.tobytes()
    
    processor = EnhancedOCRProcessor()
    result = processor.process_file(img_bytes, "test_blurred.jpg", "fra+eng")
    
    print(f"Succès: {result['success']}")
    print(f"Confiance: {result['average_confidence']:.2%}")
    print(f"Texte extrait (preview):\n{result['text'][:300]}...")
    print(f"Méthode utilisée: {result['pages'][0].get('method_used') if result.get('pages') else 'N/A'}")
    print("-" * 80)

def test_low_contrast_image():
    """Test avec une image à faible contraste"""
    print("\nTest 4: Image faible contraste")
    
    # Créer une image avec faible contraste
    img = np.ones((500, 800, 3), dtype=np.uint8) * 200  # Fond gris clair
    cv2.putText(img, "CARTE D'IDENTITE", (100, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (150, 150, 150), 2)  # Texte gris
    cv2.putText(img, "Nom: MARTIN", (100, 180), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (160, 160, 160), 2)
    cv2.putText(img, "Prenom: Sophie", (100, 230), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (160, 160, 160), 2)
    cv2.putText(img, "Né(e) le: 15/07/1985", (100, 280), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (160, 160, 160), 2)
    
    _, buffer = cv2.imencode('.jpg', img)
    img_bytes = buffer.tobytes()
    
    processor = EnhancedOCRProcessor()
    result = processor.process_file(img_bytes, "test_low_contrast.jpg", "fra+eng")
    
    print(f"Succès: {result['success']}")
    print(f"Confiance: {result['average_confidence']:.2%}")
    print(f"Informations personnelles extraites: {result.get('structured_data', {}).get('personal_info', {})}")
    print(f"Dates trouvées: {result.get('structured_data', {}).get('dates', [])}")
    print("-" * 80)

if __name__ == "__main__":
    print("=" * 80)
    print("TEST COMPLET DU SYSTÈME OCR AMÉLIORÉ")
    print("=" * 80)
    
    test_low_quality_image()
    test_high_quality_image()
    test_blurred_image()
    test_low_contrast_image()
    
    print("\n✅ Tests terminés avec succès!")# app/api/auth.py - Extrait pour contexte
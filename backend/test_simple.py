#!/usr/bin/env python3
"""
Test de l'API OCR Intelligent
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Test de l'API OCR Intelligent...")
    
    # Test 1: Vérifier que l'API est en ligne
    print("\n1. Test de santé...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   ✅ API en ligne: {response.json()}")
    except Exception as e:
        print(f"   ❌ API hors ligne: {e}")
        return False
    
    # Test 2: Connexion avec l'utilisateur démo
    print("\n2. Test d'authentification...")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "aitdjoudi@gmail.com",
            "password": "boussad"
        })
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"   ✅ Authentification réussie, token obtenu")
            
            # Test 3: Récupération des infos utilisateur
            response = requests.get(f"{BASE_URL}/api/auth/me", headers={
                "Authorization": f"Bearer {token}"
            })
            
            if response.status_code == 200:
                user = response.json()
                print(f"   ✅ Infos utilisateur: {user['username']}")
                return token
            else:
                print(f"   ❌ Échec récupération infos: {response.text}")
        else:
            print(f"   ❌ Échec authentification: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    return None

def test_ocr_upload(token):
    print("\n3. Test d'upload OCR...")
    
    # Créer une image de test simple
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Créer une image avec du texte
    img = Image.new('RGB', (800, 400), color='white')
    d = ImageDraw.Draw(img)
    
    # Ajouter du texte
    text = """Nom: Jean Dupont
Email: jean.dupont@example.com
Téléphone: +33 1 23 45 67 89
Adresse: 123 Rue de Paris, 75001 Paris
Date: 15/01/2024
Montant: 150,00 €
Facture n°: FAC-2024-001"""
    
    d.text((50, 50), text, fill='black')
    
    # Sauvegarder en bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Envoyer à l'API
    try:
        # Note: Pour ce test simple, on va simuler l'appel
        print("   ⚠️  Pour tester l'upload, utilisez le frontend ou:")
        print(f"   curl -X POST {BASE_URL}/api/ocr/process \\")
        print("        -H 'Content-Type: multipart/form-data' \\")
        print("        -F 'file=@votre_document.pdf' \\")
        print("        -F 'language=fra+eng'")
        
        print("\n   Ou ouvrez simplement le frontend dans votre navigateur!")
        
    except Exception as e:
        print(f"   ❌ Erreur upload: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🔬 Test OCR Intelligent API")
    print("="*60)
    
    token = test_api()
    
    if token:
        print("\n" + "="*60)
        print("✅ API fonctionnelle!")
        print("="*60)
        print("\n📋 Étapes suivantes:")
        print("1. Ouvrez le frontend dans votre navigateur")
        print("2. Connectez-vous avec: aitdjoudi@gmail.com / boussad")
        print("3. Téléchargez un document (PDF ou image)")
        print("4. Visualisez les résultats extraits")
        print("\n📍 URLs:")
        print(f"   • Backend:  {BASE_URL}")
        print(f"   • API Docs: {BASE_URL}/docs")
        print("   • Frontend: http://localhost:3000 (si démarré)")
    else:
        print("\n❌ L'API ne fonctionne pas correctement")
        print("   Vérifiez que le serveur est démarré avec:")
        print("   python run_simple.py")
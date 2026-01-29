#!/usr/bin/env python3
"""
Script de test pour l'authentification
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    print("🧪 Test du flux d'authentification...")
    
    # Test 1: Inscription
    print("\n1. Test d'inscription...")
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Inscription réussie: {response.json()['username']}")
        else:
            print(f"   ❌ Échec: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 2: Connexion avec mauvais mot de passe
    print("\n2. Test connexion avec mauvais mot de passe...")
    login_data = {
        "username": "demo",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Refus correct avec mauvais mot de passe")
        else:
            print(f"   ❌ Réponse inattendue: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 3: Connexion réussie
    print("\n3. Test connexion réussie...")
    login_data = {
        "username": "demo",
        "password": "demo123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"   ✅ Connexion réussie, token obtenu")
            
            # Test 4: Récupération des infos utilisateur
            print("\n4. Test récupération infos utilisateur...")
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                user_info = response.json()
                print(f"   ✅ Infos utilisateur: {user_info['username']}")
            else:
                print(f"   ❌ Échec: {response.text}")
                
            # Test 5: Rafraîchissement du token
            print("\n5. Test rafraîchissement du token...")
            response = requests.post(f"{BASE_URL}/api/auth/refresh", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                new_token = response.json()["access_token"]
                print(f"   ✅ Token rafraîchi")
            else:
                print(f"   ❌ Échec: {response.text}")
                
        else:
            print(f"   ❌ Échec de connexion: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 6: Déconnexion
    print("\n6. Test déconnexion...")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Déconnexion réussie")
        else:
            print(f"   ❌ Échec: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    print("\n" + "="*50)
    print("✅ Tests d'authentification terminés")

def test_api_endpoints():
    print("\n🧪 Test des endpoints API...")
    
    # Test 1: Health check
    print("\n1. Test health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ API en ligne: {response.json()}")
        else:
            print(f"   ❌ Échec: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 2: Documentation
    print("\n2. Test documentation...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Documentation disponible")
        else:
            print(f"   ❌ Échec: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Test 3: Endpoints OCR (avec authentification)
    print("\n3. Test endpoints OCR (nécessite authentification)...")
    try:
        # D'abord se connecter
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "demo",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Tester l'endpoint results
            response = requests.get(f"{BASE_URL}/api/results", headers=headers)
            print(f"   Status results: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Results: {len(response.json())} éléments")
            else:
                print(f"   ❌ Results échec: {response.text}")
        else:
            print(f"   ❌ Impossible de se connecter pour tester")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    print("="*50)
    print("🔬 Tests OCR Intelligent API")
    print("="*50)
    
    # Tester l'authentification
    test_auth_flow()
    
    # Tester les endpoints API
    test_api_endpoints()
    
    print("\n" + "="*50)
    print("📋 Résumé des tests")
    print("="*50)
    print("""
    Pour utiliser l'application:
    
    1. Démarrer le backend: python start.py
    2. Démarrer le frontend: cd frontend && python start.py
    3. Ouvrir http://localhost:3000
    4. Se connecter avec:
       - Utilisateur: demo
       - Mot de passe: demo123
    
    Endpoints disponibles:
    - http://localhost:8000/docs (Documentation API)
    - http://localhost:8000/api/auth/* (Authentification)
    - http://localhost:8000/api/ocr/* (Traitement OCR)
    - http://localhost:8000/api/results/* (Résultats)
    """)
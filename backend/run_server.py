#!/usr/bin/env python3
"""
Script simple pour démarrer le serveur
"""

import uvicorn
import os
import sys

# Ajouter le chemin actuel
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Démarrage du serveur OCR Intelligent...")
    print("📍 URL: http://localhost:8000")
    print("📄 Documentation: http://localhost:8000/docs")
    print("🔑 Identifiants démo: demo / demo123")
    print("\n🛑 Appuyez sur Ctrl+C pour arrêter\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
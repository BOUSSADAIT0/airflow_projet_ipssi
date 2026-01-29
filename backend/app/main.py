from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager

from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware
from app.api.ocr import router as ocr_router
from app.api.auth import router as auth_router

app = FastAPI(title="OCR Intelligent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ocr_router)
app.include_router(auth_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ocr-intelligent-api"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("="*60)
    print("🚀 OCR INTELLIGENT - API AVANCÉE")
    print("="*60)
    print("📦 Initialisation...")
    
    # Initialiser la base de données (tables + utilisateur démo)
    init_db()

    # Créer les répertoires
    directories = ['uploads', 'results', 'static', 'exports']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✅ {directory}/")
    
    print("\n📍 Endpoints disponibles:")
    print("  • http://localhost:8000/          - Accueil")
    print("  • http://localhost:8000/docs      - Documentation API")
    print("  • http://localhost:8000/health    - Santé de l'API")
    print("\n🔑 Authentification:")
    print("  • POST /api/auth/login           - Connexion")
    print("  • POST /api/auth/register        - Inscription")
    print("  • GET  /api/auth/me             - Profil utilisateur")
    print("\n📄 Traitement OCR:")
    print("  • POST /api/ocr/process         - Traiter un document")
    print("  • POST /api/ocr/batch-process   - Traiter plusieurs documents")
    print("  • GET  /api/ocr/results/{id}    - Récupérer résultats")
    print("  • GET  /api/ocr/stats           - Statistiques")
    print("\n⬇️  Téléchargement:")
    print("  • GET  /api/ocr/results/{id}/download/json")
    print("  • GET  /api/ocr/results/{id}/download/csv")
    print("  • GET  /api/ocr/results/{id}/download/txt")
    print("\n👤 Utilisateurs par défaut disponibles :")
    print("  • admin / Admin123!   (email: admin@ocri.com)")
    print("  • user / User123!     (email: user@ocri.com)")
    print("  • testeur / Test123!  (email: test@ocri.com)")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n👋 Arrêt de l'application OCR Intelligent...")

app = FastAPI(
    title="OCR Intelligent API - Édition Avancée",
    version="2.0.0",
    description="""
    API avancée d'extraction OCR intelligente.
    
    Fonctionnalités:
    - 📄 Lecture de documents scannés (PDF, images)
    - 🔍 Détection automatique du type de document
    - 👤 Extraction des informations personnelles (nom, email, téléphone)
    - 💰 Extraction des données financières (factures)
    - 📝 Structuration des données en JSON/CSV
    - 🔄 Traitement par lots
    - 📊 Statistiques détaillées
    """,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(ocr_router)

@app.get("/")
async def root():
    return {
        "application": "OCR Intelligent API",
        "version": "2.0.0",
        "description": "API avancée d'extraction OCR de documents",
        "endpoints": {
            "documentation": "/docs",
            "authentication": "/api/auth",
            "ocr_processing": "/api/ocr",
            "health_check": "/health"
        },
        "features": [
            "Lecture de documents scannés (PDF, images)",
            "Détection automatique du type de document",
            "Extraction des informations personnelles",
            "Structuration des données en JSON/CSV",
            "Téléchargement des résultats",
            "Statistiques détaillées"
        ]
    }

@app.get("/health")
async def health():
    import psutil
    return {
        "status": "healthy",
        "timestamp": "2024-01-15T10:30:00Z",
        "system": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        },
        "api": {
            "version": "2.0.0",
            "endpoints_available": True
        }
    }

# Servir les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/results", StaticFiles(directory="results"), name="results")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Ne fait rien pour le moment
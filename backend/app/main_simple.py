from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
import os
import pytesseract
from PIL import Image
import pdf2image
import io
import re
import json
from typing import Dict, Any, List
import uuid
import tempfile
import subprocess
from app.services.image_processing import preprocess_image
from app.services.extraction import extract_structured_data

app = FastAPI(
    title="OCR Intelligent API",
    version="1.0.0",
    description="API simple d'extraction OCR"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = "ocr-intelligent-secret-key-2024"
ALGORITHM = "HS256"

# Modèles
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True

# Base de données utilisateurs
users_db = {}

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)  # Token valide 24 h (au lieu de 1 h)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Initialiser les utilisateurs
demo_user = {
    "id": 1,
    "username": "aitdjoudi@gmail.com",
    "email": "aitdjoudi@gmail.com",
    "full_name": "Boussad",
    "hashed_password": get_password_hash("boussad"),
    "is_active": True
}
users_db["aitdjoudi@gmail.com"] = demo_user

# Dépendance pour l'authentification
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant")
    
    try:
        # Extraire le token du header "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Format d'authentification invalide")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if not username or username not in users_db:
            raise HTTPException(status_code=401, detail="Token invalide")
        
        user = users_db[username]
        return User(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            is_active=user["is_active"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    except ValueError:
        raise HTTPException(status_code=401, detail="Format de token invalide")

# Routes d'authentification
@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = users_db.get(user_data.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token, token_type="bearer")

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    """Inscription d'un nouvel utilisateur"""
    # Vérifier si l'utilisateur existe déjà
    if user_data.username in users_db or user_data.email in [u["email"] for u in users_db.values()]:
        raise HTTPException(status_code=400, detail="Cet utilisateur ou email existe déjà")
    
    # Créer le nouvel utilisateur
    new_user = {
        "id": len(users_db) + 1,
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name or user_data.username,
        "hashed_password": get_password_hash(user_data.password),
        "is_active": True
    }
    
    users_db[user_data.username] = new_user
    
    # Créer et retourner un token
    access_token = create_access_token(data={"sub": user_data.username})
    return Token(access_token=access_token, token_type="bearer")

@app.get("/api/auth/me", response_model=User)
async def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté"""
    return current_user

# Fonctions OCR
def extract_text_from_image(image_bytes: bytes, language: str = "fra+eng") -> Dict[str, Any]:
    """Extrait le texte d'une image"""
    try:
        # Preprocess image for better OCR
        processed_image = preprocess_image(image_bytes)
        
        # Extraire le texte
        text = pytesseract.image_to_string(processed_image, lang=language)
        
        # Extraire les données
        data = pytesseract.image_to_data(processed_image, lang=language, output_type=pytesseract.Output.DICT)
        
        # Calculer la confiance
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0
        
        return {
            "text": text,
            "confidence": avg_confidence,
            "word_count": len([w for w in data['text'] if w.strip()])
        }
        
    except Exception as e:
        print(f"OCR Error: {e}")
        # Fallback to simple extraction if preprocessing fails
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=language)
            return {"text": text, "confidence": 0.5, "word_count": 0}
        except Exception as e2:
            raise HTTPException(status_code=400, detail=f"Erreur OCR: {str(e2)}")

def extract_text_from_pdf(pdf_bytes: bytes, language: str = "fra+eng") -> List[Dict[str, Any]]:
    """Extrait le texte d'un PDF"""
    try:
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=200)
        results = []
        
        for i, image in enumerate(images):
            # Convertir en bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Extraire le texte
            page_result = extract_text_from_image(img_byte_arr, language)
            page_result["page"] = i + 1
            results.append(page_result)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur PDF: {str(e)}")

def extract_text_from_pages(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier .pages via textutil (macOS only)"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.pages', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        try:
            # textutil -convert txt input.pages -stdout
            result = subprocess.run(
                ['textutil', '-convert', 'txt', tmp_path, '-stdout'], 
                capture_output=True, 
                check=True
            )
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError:
            return ""
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        print(f"Error converting .pages: {e}")
        return ""

def extract_personal_info(text: str) -> Dict[str, Any]:
    """Extrait les informations personnelles du texte"""
    info = {
        "names": [],
        "emails": [],
        "phones": [],
        "dates": [],
        "addresses": [],
        "amounts": []
    }
    
    # Noms (simple pattern)
    name_patterns = [
        r'(?:nom|name)\s*[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'm\.\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'mme\.\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            info["names"].extend([m.strip() for m in matches])
    
    # Emails
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if emails:
        info["emails"] = list(set(emails))
    
    # Téléphones
    phone_patterns = [
        r'(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
        r'tel[.:]?\s*([\d\s\-\+\(\)]{8,})'
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            for phone in phones:
                if isinstance(phone, str):
                    info["phones"].append(phone.strip())
                elif phone[0]:
                    info["phones"].append(phone[0].strip())
    
    # Dates
    dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}/\d{1,2}/\d{1,2}', text)
    if dates:
        info["dates"] = list(set(dates))
    
    # Adresses (simplifié)
    address_patterns = [
        r'adresse\s*[.:]\s*([^\n]{10,50})',
        r'(\d+\s+[a-zA-Z\s]+(?:rue|avenue|boulevard)[^\n]{5,40})'
    ]
    
    for pattern in address_patterns:
        addresses = re.findall(pattern, text, re.IGNORECASE)
        if addresses:
            for addr in addresses:
                if isinstance(addr, str):
                    info["addresses"].append(addr.strip())
                elif addr[0]:
                    info["addresses"].append(addr[0].strip())
    
    # Montants
    amounts = re.findall(r'[\d,]+\.?\d*\s*[€$]|\d+\.\d{2}', text)
    if amounts:
        info["amounts"] = list(set(amounts))
    
    return info

def detect_document_type(text: str, filename: str) -> str:
    """Détecte le type de document"""
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Détection basée sur les mots-clés
    # Détection basée sur les mots-clés
    if any(word in text_lower for word in ['facture', 'invoice', 'montant', 'total', 'tva', 'ttc']):
        return 'invoice'
    elif any(word in text_lower for word in ['cv', 'curriculum', 'expérience', 'compétence', 'education', 'skills']):
        return 'cv'
    elif any(word in text_lower for word in ['exercice', 'exercise', 'question', 'réponse', 'devoir', 'homework']):
        return 'exercise'
    elif any(word in text_lower for word in ['essay', 'dissertation', 'thèse', 'introduction', 'conclusion', 'tpe']):
        return 'essay'
    elif any(word in text_lower for word in ['contrat', 'contract', 'agreement', 'signature']):
        return 'contract'
    
    return 'document'

# Routes OCR
@app.post("/api/ocr/extract")
async def extract_ocr(
    file: UploadFile = File(...),
    language: str = Form("fra+eng"),
    current_user: User = Depends(get_current_user)
):
    """Traite un document avec OCR (version simplifiée)"""
    try:
        # Lire le fichier
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Fichier vide")

        # Sauvegarder une copie dans uploads/ pour que le PythonSensor Airflow puisse le voir (même dossier = backend/uploads)
        uploads_dir = os.path.join("uploads", "inbox")
        os.makedirs(uploads_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        with open(os.path.join(uploads_dir, safe_name), "wb") as f:
            f.write(content)
        
        all_text = ""
        pages = []
        
        # Déterminer le type de fichier
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if file_ext == 'pdf':
            # Traitement PDF
            pdf_results = extract_text_from_pdf(content, language)
            for result in pdf_results:
                all_text += f"--- Page {result['page']} ---\n{result['text']}\n\n"
                pages.append(result)
        elif file_ext == 'pages':
            # Traitement .pages
            text = extract_text_from_pages(content)
            all_text = text
            pages = [{"page": 1, "text": text, "confidence": 1.0}]
        else:
            # Traitement image
            result = extract_text_from_image(content, language)
            all_text = result["text"]
            pages = [{"page": 1, **result}]
        
        if not all_text.strip():
            raise HTTPException(status_code=400, detail="Aucun texte extrait")
        
        # Détection du type de document
        doc_type = detect_document_type(all_text, file.filename)
        
        # Extraction des informations personnelles et structurées
        structured_data = extract_structured_data(all_text, doc_type)
        personal_info = extract_personal_info(all_text) # Keep legacy function for backward compatibility if needed, or merge
        
        # Créer la réponse
        process_id = str(uuid.uuid4())
        
        result = {
            "success": True,
            "process_id": process_id,
            "filename": file.filename,
            "document_type": doc_type,
            "total_pages": len(pages),
            "text": all_text,
            "text": all_text,
            "pages": pages,
            "personal_info": personal_info, # Legacy
            "structured_data": structured_data, # New detailed data
            "average_confidence": sum(p.get('confidence', 0) for p in pages) / len(pages) if pages else 0,
            "average_confidence": sum(p.get('confidence', 0) for p in pages) / len(pages) if pages else 0,
            "processing_date": datetime.now().isoformat(),
            "user": current_user.username
        }
        
        # Sauvegarder le résultat
        os.makedirs("results", exist_ok=True)
        with open(f"results/{process_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/api/ocr/results/{process_id}")
async def get_results(process_id: str, current_user: User = Depends(get_current_user)):
    """Récupère les résultats d'un traitement"""
    filepath = f"results/{process_id}.json"
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Résultats non trouvés")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        # Vérifier que l'utilisateur a accès à ces résultats
        if result.get("user") != current_user.username and current_user.username != "aitdjoudi@gmail.com":
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        return result
    except:
        raise HTTPException(status_code=500, detail="Erreur de lecture")

@app.get("/api/ocr/download/{process_id}/{format}")
async def download_results(
    process_id: str,
    format: str,  # json, txt, csv
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Télécharge les résultats dans différents formats. Supporte soit l'entête Authorization, soit `?token=` en query param."""
    filepath = f"results/{process_id}.json"
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Résultats non trouvés")
    
    # Valider le token s'il est présent en query param, ou utiliser l'en-tête Authorization
    current_username = None
    try:
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_username = payload.get("sub")
        elif authorization:
            scheme, auth_token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Format d'authentification invalide")
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            current_username = payload.get("sub")
        else:
            raise HTTPException(status_code=401, detail="Token manquant")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        # Vérifier que l'utilisateur a accès à ces résultats
        # Si le résultat n'a pas d'attribut 'user', le rendre public
        if result.get("user") and result.get("user") != current_username and current_username != "demo":
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        if format == "json":
            return result
        elif format == "txt":
            from fastapi.responses import PlainTextResponse
            text = result.get("text", "")
            return PlainTextResponse(text, media_type="text/plain", 
                                   headers={"Content-Disposition": f"attachment; filename={process_id}.txt"})
        elif format == "csv":
            # Convertir en CSV simple
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow(["Champ", "Valeur"])
            
            # Informations de base
            writer.writerow(["Nom du fichier", result.get("filename", "")])
            writer.writerow(["Type de document", result.get("document_type", "")])
            writer.writerow(["Pages", result.get("total_pages", 0)])
            writer.writerow(["Confiance moyenne", f"{result.get('average_confidence', 0)*100:.1f}%"])
            
            # Informations personnelles et structurées
            structured_data = result.get("structured_data", {})
            if structured_data:
                 for key, value in structured_data.items():
                    if isinstance(value, list):
                        writer.writerow([f"Data - {key}", ", ".join(str(v) for v in value)])
                    elif isinstance(value, dict):
                         writer.writerow([f"Data - {key}", json.dumps(value, ensure_ascii=False)])
                    else:
                        writer.writerow([f"Data - {key}", str(value)])
            else:
                # Fallback old personal_info
                personal_info = result.get("personal_info", {})
                for key, values in personal_info.items():
                    if values:
                        writer.writerow([f"Info - {key}", ", ".join(values) if isinstance(values, list) else values])
            
            # Retourner le CSV
            from fastapi.responses import PlainTextResponse
            csv_content = output.getvalue()
            return PlainTextResponse(csv_content, media_type="text/csv",
                                   headers={"Content-Disposition": f"attachment; filename={process_id}.csv"})
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/ocr/history")
async def get_history(current_user: User = Depends(get_current_user)):
    """Récupère l'historique des traitements"""
    try:
        if not os.path.exists("results"):
            return {"history": []}
        
        files = [f for f in os.listdir("results") if f.endswith('.json')]
        history = []
        
        for file in files[-10:]:  # Derniers 10 fichiers
            try:
                with open(f"results/{file}", "r", encoding="utf-8") as f:
                    result = json.load(f)
                
                # Filtrer par utilisateur (sauf pour démo)
                if current_user.username == "aitdjoudi@gmail.com" or result.get("user") == current_user.username:
                    history.append({
                        "process_id": file.replace(".json", ""),
                        "filename": result.get("filename", ""),
                        "document_type": result.get("document_type", ""),
                        "date": result.get("processing_date", ""),
                        "timestamp": result.get("processing_date", ""),
                        "confidence": result.get("average_confidence", 0),
                        "average_confidence": result.get("average_confidence", 0),
                        "total_pages": len(result.get("pages", [])) or 1
                    })
            except:
                continue
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/")
async def root():
    return {
        "application": "OCR Intelligent API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "login": "POST /api/auth/login",
                "me": "GET /api/auth/me (Header: Authorization: Bearer <token>)"
            },
            "ocr": {
                "extract": "POST /api/ocr/extract",
                "results": "GET /api/ocr/results/{id}",
                "download": "GET /api/ocr/download/{id}/{format}",
                "history": "GET /api/ocr/history"
            },
            "health": "GET /health"
        },
        "demo_credentials": {
            "username": "aitdjoudi@gmail.com",
            "password": "boussad"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🚀 OCR Intelligent API - Version Simplifiée")
    print("="*60)
    print("📍 URL: http://localhost:8000")
    print("📄 Docs: http://localhost:8000/docs")
    print("🔑 Demo: aitdjoudi@gmail.com / boussad")
    print("\n🛑 Ctrl+C pour arrêter")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
# Dockerfile Backend - OCR Intelligent
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    tesseract-ocr-deu \
    libtesseract-dev \
    poppler-utils \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code du backend
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p uploads results exports logs

# Exposer le port
EXPOSE 8000

# Variables d'environnement
ENV PYTHONUNBUFFERED=1

# Commande de démarrage
CMD ["uvicorn", "app.main_simple:app", "--host", "0.0.0.0", "--port", "8000"]

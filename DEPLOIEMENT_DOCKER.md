# 🐳 Guide de Déploiement Docker - OCR Intelligent

## 📋 Prérequis

1. **Docker** installé sur votre machine
   ```bash
   # Vérifier l'installation
   docker --version
   docker-compose --version
   ```

2. **Au moins 2 GB de RAM disponible**
3. **5 GB d'espace disque**

---

## 🚀 Déploiement en Local

### 1️⃣ Méthode Simple (Recommandé)

```bash
# Depuis la racine du projet
docker-compose up -d
```

C'est tout ! 🎉

### 2️⃣ Vérifier que tout fonctionne

```bash
# Voir les logs
docker-compose logs -f

# Vérifier les conteneurs
docker-compose ps
```

Vous devriez voir :
```
NAME              STATUS         PORTS
ocr-backend       Up             0.0.0.0:8000->8000/tcp
ocr-frontend      Up             0.0.0.0:80->80/tcp
```

### 3️⃣ Accéder à l'application

- **Frontend** : http://localhost
- **Backend API** : http://localhost:8000/docs
- **Tests** : http://localhost/login.html

### 4️⃣ Arrêter l'application

```bash
# Arrêter les conteneurs
docker-compose down

# Arrêter ET supprimer les volumes
docker-compose down -v
```

---

## 🌐 Déploiement en Production

### Option 1 : VPS (DigitalOcean, AWS EC2, etc.)

```bash
# 1. Se connecter au serveur
ssh user@votre-serveur.com

# 2. Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Cloner le projet
git clone https://github.com/safaafaraji/Inteligent_OCR.git
cd Inteligent_OCR

# 5. Démarrer
docker-compose up -d

# 6. Configurer un nom de domaine (optionnel)
# Installer nginx et certbot pour HTTPS
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com
```

### Option 2 : Heroku

```bash
# 1. Installer Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# 2. Se connecter
heroku login

# 3. Créer une app
heroku create ocr-intelligent-app

# 4. Ajouter le buildpack
heroku buildpacks:add heroku/python

# 5. Définir les variables
heroku config:set SECRET_KEY=votre-secret-key-production

# 6. Déployer
git push heroku main
```

### Option 3 : Railway.app (Plus Simple)

1. Allez sur https://railway.app
2. Connectez votre compte GitHub
3. Cliquez sur "New Project" → "Deploy from GitHub repo"
4. Sélectionnez `Inteligent_OCR`
5. Railway détecte automatiquement Docker et déploie ! 🚀

---

## 🔧 Configuration Avancée

### Modifier les Ports

Éditez `docker-compose.yml` :

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Au lieu de 8000:8000
  
  frontend:
    ports:
      - "3000:80"    # Au lieu de 80:80
```

### Variables d'Environnement

Créez un fichier `.env` :

```env
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,votre-domaine.com
DEBUG=False
```

Puis dans `docker-compose.yml` :

```yaml
services:
  backend:
    env_file:
      - .env
```

### Sauvegardes

```bash
# Sauvegarder les uploads et résultats
docker run --rm -v $(pwd)/backend/uploads:/backup alpine tar czf /backup/uploads-backup.tar.gz /backup

# Restaurer
docker run --rm -v $(pwd)/backend/uploads:/backup alpine tar xzf /backup/uploads-backup.tar.gz
```

---

## 🐛 Dépannage

### Problème : "Port already in use"

```bash
# Trouver et tuer le processus
sudo lsof -ti:8000 | xargs kill -9
sudo lsof -ti:80 | xargs kill -9
```

### Problème : "No space left on device"

```bash
# Nettoyer Docker
docker system prune -a --volumes
```

### Problème : Build échoue

```bash
# Rebuild sans cache
docker-compose build --no-cache
docker-compose up -d
```

### Voir les logs en temps réel

```bash
# Tous les services
docker-compose logs -f

# Backend uniquement
docker-compose logs -f backend

# Frontend uniquement
docker-compose logs -f frontend
```

---

## 📊 Monitoring

### Vérifier l'utilisation des ressources

```bash
docker stats
```

### Healthcheck

```bash
# Backend
curl http://localhost:8000/api/auth/login

# Frontend
curl http://localhost
```

---

## 🔐 Sécurité en Production

1. **Changer le SECRET_KEY** dans `backend/app/main_simple.py`
2. **Activer HTTPS** avec Let's Encrypt
3. **Limiter les CORS** dans le backend
4. **Utiliser un reverse proxy** (Nginx/Traefik)
5. **Mettre à jour régulièrement** les images Docker

```bash
# Mettre à jour
docker-compose pull
docker-compose up -d
```

---

## ✅ Checklist de Déploiement

- [ ] Docker et Docker Compose installés
- [ ] Variables d'environnement configurées
- [ ] Ports 80 et 8000 disponibles
- [ ] `docker-compose up -d` fonctionne
- [ ] Backend accessible sur port 8000
- [ ] Frontend accessible sur port 80
- [ ] Login fonctionne avec demo/demo123
- [ ] Upload de fichier fonctionne
- [ ] Téléchargement JSON/CSV fonctionne

---

## 🎯 Commandes Rapides

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Voir les logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache

# Entrer dans un conteneur
docker exec -it ocr-backend bash
docker exec -it ocr-frontend sh
```

---

Bon déploiement ! 🚀

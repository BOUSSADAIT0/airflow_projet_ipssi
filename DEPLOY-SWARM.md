# Déploiement Docker Swarm (OCR + Airflow + Traefik)

Ce guide permet de déployer l’application en ligne avec **Docker Swarm** et **Traefik**. Tout est exposé sur **un seul port (80)** avec des chemins différents.

## URLs après déploiement

| Chemin     | Service   | Description                    |
|-----------|-----------|--------------------------------|
| `/`       | Frontend  | Interface OCR                  |
| `/api`    | Backend   | API (auth, OCR, etc.)          |
| `/airflow`| Airflow   | Interface Airflow (admin/admin)|
| `:8081`   | Traefik   | Dashboard Traefik (optionnel)  |

Exemple : si le serveur a l’IP `192.168.1.10` :
- **App** : http://192.168.1.10/
- **API** : http://192.168.1.10/api/health
- **Airflow** : http://192.168.1.10/airflow

Avec un **nom de domaine** (ex. `ocr.example.com`) : même chose en remplaçant l’IP par le domaine.

---

## 1. Prérequis

- **Serveur** (VPS) avec Docker installé.
- Accès SSH (ou console) sur le serveur.

Sur le serveur :

```bash
docker --version   # 20.10+
```

---

## 2. Initialiser Swarm (une fois)

Sur la machine qui sera le manager (souvent votre seul nœud) :

```bash
docker swarm init
```

Si vous avez une seule machine, c’est suffisant. Pour plusieurs nœuds, voir la doc Docker Swarm.

---

## 3. Builder et taguer les images

Les services **backend** et **frontend** doivent être buildés et tagués. À faire **depuis votre machine** (ou depuis le serveur si le code y est cloné).

À la racine du projet (là où se trouvent `backend/` et `frontend/`) :

```bash
# Backend
docker build -t ocr-backend:latest ./backend

# Frontend
docker build -t ocr-frontend:latest ./frontend
```

Si vous déployez sur un **autre serveur** :

- Soit vous faites le build **sur le serveur** après avoir cloné/copié le projet.
- Soit vous poussez les images vers un **registry** (Docker Hub, GitHub Container Registry, etc.) et sur le serveur vous faites `docker pull votre-registry/ocr-backend:latest` puis vous adaptez les noms d’images dans `docker-compose.swarm.yml`.

---

## 4. Déployer la stack

Sur le **manager** (même répertoire que `docker-compose.swarm.yml`) :

```bash
# Optionnel : domaine ou IP pour les liens Airflow
export DOMAIN=192.168.1.10
# ou avec un nom de domaine :
# export DOMAIN=ocr.example.com

# Optionnel : credentials Airflow (DAG OCR)
export OCR_USERNAME=votre@email.com
export OCR_PASSWORD=votre_mot_de_passe

# Déploiement
docker stack deploy -c docker-compose.swarm.yml ocr
```

Vérifier que les services tournent :

```bash
docker stack services ocr
docker stack ps ocr
```

---

## 5. DAGs Airflow (volume vide au départ)

Le volume `airflow_dags` est créé vide. Pour avoir vos DAGs :

**Option A – Copier après le premier déploiement**

```bash
# Trouver le conteneur du service airflow
docker ps | grep airflow

# Copier le dossier dags du projet vers le volume (Linux/Mac : depuis la racine du projet)
docker run --rm -v ocr_airflow_dags:/opt/airflow/dags -v "$(pwd)/airflow/dags:/source" alpine cp -r /source/. /opt/airflow/dags/

# Sous Windows PowerShell (depuis la racine du projet) :
# docker run --rm -v ocr_airflow_dags:/opt/airflow/dags -v "${PWD}/airflow/dags:/source" alpine cp -r /source/. /opt/airflow/dags/
```

**Option B – Bind mount (si le code est sur le serveur)**

Éditer `docker-compose.swarm.yml` pour le service `airflow` : remplacer le volume nommé par un bind mount vers votre dossier `airflow/dags` sur l’hôte (chemin absolu sur le nœud manager).

---

## 6. Arrêter / supprimer la stack

```bash
docker stack rm ocr
```

Les **volumes** (données PostgreSQL, uploads, etc.) restent. Pour tout supprimer (y compris les volumes), il faut les supprimer après `stack rm` :

```bash
docker volume ls | grep ocr_
docker volume rm ocr_backend_uploads ocr_backend_results ocr_backend_exports ocr_airflow_postgres_data ocr_airflow_logs ocr_airflow_dags
```

---

## 7. Résumé des commandes

```bash
# Une fois
docker swarm init

# Build des images (depuis la racine du projet)
docker build -t ocr-backend:latest ./backend
docker build -t ocr-frontend:latest ./frontend

# Déploiement (optionnel : export DOMAIN=... et OCR_*)
docker stack deploy -c docker-compose.swarm.yml ocr

# Vérification
docker stack services ocr

# Suppression
docker stack rm ocr
```

---

## 8. HTTPS (optionnel)

Pour activer **HTTPS** avec Traefik (Let’s Encrypt) :

1. Avoir un **nom de domaine** pointant vers l’IP du serveur.
2. Ajouter dans le service `traefik` de `docker-compose.swarm.yml` :
   - un entrypoint `websecure` (port 443),
   - le provider **acme** (Let’s Encrypt),
   - et faire pointer les routers vers `websecure` au lieu de `web`.

Voir la doc Traefik : [HTTPS / ACME](https://doc.traefik.io/traefik/https/overview/).

# Intégration Apache Airflow - OCR Intelligent

Airflow permet d’**orchestrer** le traitement OCR par lots : exécution planifiée ou manuelle, surveillance des tâches et réessais en cas d’échec.

## Rôle d’Airflow dans le projet

- **Planification** : lancer un traitement par lots de documents (ex. toutes les heures).
- **Orchestration** : enchaîner login API → liste des fichiers → envoi à l’API OCR.
- **Monitoring** : voir l’historique des runs et les logs dans l’interface Airflow.

Le DAG fourni appelle l’**API OCR** (backend FastAPI) : il ne refait pas l’OCR lui‑même, il envoie les fichiers vers `POST /api/ocr/extract`.

---

## Démarrage avec Docker

### Prérequis

- Docker et Docker Compose.
- Backend OCR déjà défini dans `docker-compose.yml` (services `backend`, `frontend`).

### Lancer backend + frontend + Airflow

```bash
docker-compose -f docker-compose.yml -f docker-compose.airflow.yml up -d
```

- **Backend OCR** : http://localhost:8000  
- **Frontend** : http://localhost:80  
- **Airflow** : http://localhost:8080  

### Premier accès Airflow

1. Ouvrir http://localhost:8080  
2. Connexion : **admin** / **admin** (à changer dans Airflow après la 1ère connexion).  
3. Le DAG **`ocr_batch_pipeline`** apparaît dans la liste (parfois après 1–2 minutes).

---

## Utilisation du DAG `ocr_batch_pipeline`

### Flux des tâches (visible dans l’interface Airflow)

1. **start** – Démarrage du pipeline.  
2. **wait_for_file** (PythonSensor) – Attend qu’au moins un fichier (PDF/image) soit présent dans l’inbox. Vérification toutes les 30 s, timeout 1 h.  
3. **get_token_task** – Récupère le token JWT auprès de l’API OCR.  
4. **list_files_task** – Liste les chemins des fichiers à traiter (inbox + sous-dossiers).  
5. **process_file_task** (× N) – Une tâche par fichier : envoi à `POST /api/ocr/extract`.  
6. **resume_task** – Résumé (nombre de fichiers traités).  
7. **end** – Fin du pipeline.

### Déclenchement dès qu’un fichier est uploadé dans l’app

- Avec Docker, l’**inbox** Airflow est le même dossier que les **uploads** du backend : `./backend/uploads` est monté en `/opt/airflow/inbox`.  
- Dès qu’un utilisateur envoie un fichier via l’application (frontend), le backend le sauvegarde dans `uploads/` (ou un sous-dossier).  
- Le DAG tourne **toutes les 1 minute**. À chaque run, le **PythonSensor** attend qu’au moins un fichier soit présent ; dès qu’un fichier apparaît, le sensor débloque et le reste du pipeline s’exécute (token → liste → traitement par fichier).

### Dossier inbox (fichiers à traiter)

- **Avec Docker** : l’inbox est **partagé avec le backend** : `./backend/uploads` → `/opt/airflow/inbox`. Les fichiers uploadés dans l’app sont donc vus par Airflow (y compris sous-dossiers `documents/`, `temp/`, etc.).  
- Vous pouvez aussi déposer des PDF/images manuellement dans `./backend/uploads` (ou un sous-dossier).

### Planification

- Par défaut le DAG est planifié **toutes les 1 minute** (`schedule_interval=timedelta(minutes=1)`).  
- À chaque run, le sensor attend jusqu’à 1 h qu’un fichier arrive ; dès qu’un fichier est présent, le traitement se lance.  
- Pour exécution **uniquement manuelle** : dans le DAG, mettre `schedule_interval=None`.

### Déclencher un run à la main

1. Aller sur http://localhost:8080 → DAGs.  
2. Activer le DAG **`ocr_batch_pipeline`** (toggle à « On »).  
3. Cliquer sur le nom du DAG → **Trigger DAG** (bouton play).

---

## Configuration (Variables Airflow)

Dans l’interface Airflow : **Admin** → **Variables**, ajouter ou modifier :

| Variable          | Description                    | Exemple (Docker)        |
|-------------------|--------------------------------|-------------------------|
| `ocr_api_url`     | URL de l’API OCR               | `http://backend:8000`    |
| `ocr_inbox_path`  | Dossier des fichiers à traiter | `/opt/airflow/inbox`    |
| `ocr_username`   | Utilisateur API OCR            | `aitdjoudi@gmail.com`   |
| `ocr_password`   | Mot de passe API OCR           | `boussad`               |

En local (sans Docker), mettre par exemple `ocr_api_url` = `http://localhost:8000` et un chemin local pour `ocr_inbox_path` si besoin.

---

## Structure des fichiers Airflow

```
airflow/
├── dags/
│   └── ocr_pipeline_dag.py   # DAG OCR par lots
├── inbox/                     # Déposer ici les PDF/images à traiter (Docker)
└── README ou ce fichier
```

---

## Dépannage

- **Le DAG n’apparaît pas** : attendre 1–2 min, vérifier les logs du conteneur `ocr-airflow` et qu’il n’y a pas d’erreur Python dans `airflow/dags/ocr_pipeline_dag.py`.  
- **Erreur de connexion à l’API** : vérifier que le backend tourne (`http://localhost:8000/health`) et que `ocr_api_url` pointe bien vers le backend (dans Docker : `http://backend:8000`).  
- **Aucun fichier traité** : vérifier que des fichiers (PDF, images) sont bien dans `airflow/inbox/` et que `ocr_inbox_path` dans Airflow correspond à ce dossier dans le conteneur (`/opt/airflow/inbox`).

---

## Arrêter les services

```bash
docker-compose -f docker-compose.yml -f docker-compose.airflow.yml down
```

Pour supprimer aussi les volumes (base Airflow, logs) :

```bash
docker-compose -f docker-compose.yml -f docker-compose.airflow.yml down -v
```

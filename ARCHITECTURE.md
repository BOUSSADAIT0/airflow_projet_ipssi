# 🏗️ Architecture du projet – Front, Back, Airflow

Ce document décrit **où se trouve chaque partie du code** (frontend, backend, Airflow) et **comment elles communiquent** entre elles.

---

## 📍 1. OÙ EST LE CODE ?

### 🖥️ FRONTEND (interface utilisateur)

| Emplacement | Rôle |
|------------|------|
| **`templates/index.html`** | **Toute l’interface web** : page unique (HTML + CSS + JavaScript) pour upload, choix de méthode OCR, affichage des résultats, export Excel/JSON. |

- **Technologies** : HTML5, CSS3, JavaScript (pas de framework type React/Vue).
- **Accès** : affiché par Flask quand on ouvre `http://localhost:5000`.
- Le front appelle le **backend** via des requêtes **fetch()** vers les routes `/api/*` (voir schéma plus bas).

---

### ⚙️ BACKEND (logique métier + API)

| Fichier | Rôle |
|---------|------|
| **`web_app.py`** | **Application Flask** : routes (pages + API REST), upload de fichiers, orchestration des appels au service de traitement. |
| **`invoice_processor.py`** | **Service de traitement des factures** : OCR (Ollama/Tesseract), parsing, export Excel. Utilisé à la fois par le **backend web** et par les **tâches Airflow**. |

**Routes principales (API utilisées par le front) :**

- `GET /` → sert `templates/index.html` (frontend).
- `POST /api/upload` → enregistre un fichier dans `uploads/`.
- `POST /api/process` → traite une facture (appelle `invoice_processor`).
- `POST /api/batch` → traitement par lot.
- `POST /api/export/excel` → export Excel.
- `GET /api/status` → statut de l’app (healthcheck).
- `GET /api/history` → historique si implémenté.

Le backend **ne parle pas directement à Airflow** : il expose une API ; Airflow, lui, utilise les **mêmes dossiers** (`uploads/`, `data/`) et le **même module** `invoice_processor.py` pour traiter les factures en automatique.

---

### 🔄 AIRFLOW (orchestration et automatisation)

| Emplacement | Rôle |
|------------|------|
| **`dags/`** | **Tous les DAGs** : définition des workflows (tâches, ordre, planification). |

**DAGs présents :**

| Fichier | DAG ID | Rôle |
|---------|--------|------|
| `d1_hello_world.py` | hello_world | DAG de démo simple. |
| `d2_xcom_pipeline.py` | xcom_pipeline | Démo XCom (échange de données entre tâches). |
| `d3_etl_api_to_postgres.py` | d3_etl_api_to_postgres | ETL : API mock → CSV → qualité → Parquet → PostgreSQL. |
| `d4_sla_and_retries.py` | d4_sla_and_retries | Exemple SLA et retries. |
| **`d5_invoice_processing.py`** | **`projet_facture`** | **Traitement automatique des factures** : scan de `uploads/`, traitement via `invoice_processor`, validation, rapport. |

**Points importants côté Airflow :**

- Les tâches s’exécutent **dans le conteneur Airflow** (scheduler/workers).
- Les DAGs ont accès au disque via les **volumes Docker** :
  - `./dags` → `/opt/airflow/dags`
  - `./data` → `/opt/airflow/data`
- Le DAG **projet_facture** utilise le dossier **`uploads/`** du projet (monté ou résolu via chemins relatifs au repo). Il **n’appelle pas** l’API Flask : il **relit les fichiers** et réutilise **`invoice_processor.py`** (en ajoutant le répertoire parent au `sys.path` pour importer le module).

---

## 🔗 2. COMMENT ÇA COMMUNIQUE ?

### Schéma global

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UTILISATEUR (navigateur)                         │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    │  http://localhost:5000
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND                    │  BACKEND                                  │
│  templates/index.html        │  web_app.py (Flask)                       │
│  (HTML + CSS + JS)           │  - Routes / et /api/*                     │
│  - Upload (drag & drop)      │  - Upload → enregistre dans uploads/     │
│  - Appels fetch() → /api/*   │  - /api/process → appelle                 │
│  - Affichage résultats       │    invoice_processor.py                  │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
                               │  import + InvoiceProcessor()
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LOGIQUE MÉTIER PARTAGÉE                                                 │
│  invoice_processor.py                                                    │
│  - OCR (Ollama / Tesseract)                                              │
│  - Parsing factures, export Excel                                        │
└─────────────────────────────────────────────────────────────────────────┘
         ▲                                              ▲
         │                                              │
         │  Même module importé                         │  Même module importé
         │  (depuis web_app.py)                         │  (depuis dags/d5_...)
         │                                              │
┌────────┴──────────────┐                    ┌──────────┴────────────────────┐
│  BACKEND (invoice-web)│                    │  AIRFLOW (scheduler)          │
│  Conteneur Flask      │                    │  DAG projet_facture          │
│  Port 5000            │                    │  - Lit uploads/ (fichiers)   │
│  Volumes: .:/app,     │                    │  - Traite avec               │
│  uploads, data        │                    │    invoice_processor        │
└───────────────────────┘                    │  - Écrit data/ (rapports)    │
                                             └──────────────────────────────┘
```

### Échanges Front ↔ Back

- **Frontend** : uniquement des requêtes HTTP vers `http://localhost:5000/api/...` (upload, process, export, etc.).
- **Backend** : reçoit les requêtes, lit/écrit les fichiers dans `uploads/` et `data/`, et utilise **`invoice_processor.py`** pour le traitement. Il **ne communique pas** avec Airflow (pas d’appel HTTP vers Airflow).

### Échanges Back / Airflow ↔ `invoice_processor`

- **Backend** : dans `web_app.py`, `from invoice_processor import InvoiceProcessor` puis `processor.process_invoice(...)` etc.
- **Airflow** : dans `d5_invoice_processing.py`, les tâches font :
  - `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))`
  - `from invoice_processor import InvoiceProcessor`
  - puis appellent les mêmes méthodes (process_invoice, export_to_excel, etc.).

Donc **le lien entre Back et Airflow** est :
1. **Partage du même code métier** : `invoice_processor.py`.
2. **Partage des mêmes dossiers** (via Docker) : `uploads/` et `data/` pour lire les factures et écrire les résultats/rapports.

### Autre lien : ETL API → Postgres (DAG d3)

- Le DAG **d3_etl_api_to_postgres** appelle l’**API mock** : `http://mock-api:8099/orders`.
- **Mock API** : `scripts/mock_api.py`, servi dans un conteneur à part (port 8099), lit `data/orders.csv` et renvoie du JSON.
- Donc ici la communication est **Airflow → HTTP → mock-api** ; pas de lien avec le front/back des factures.

---

## 📂 3. RÉCAPITULATIF DES FICHIERS IMPORTANTS

| Rôle | Fichiers / Dossiers |
|------|---------------------|
| **Frontend** | `templates/index.html` |
| **Backend (API + pages)** | `web_app.py` |
| **Logique métier (factures)** | `invoice_processor.py` |
| **Airflow (workflows)** | `dags/*.py` (dont `d5_invoice_processing.py` → DAG `projet_facture`) |
| **API utilisée par DAG ETL** | `scripts/mock_api.py` |
| **Données partagées** | `uploads/`, `data/` |
| **Config globale** | `docker-compose.yml`, `requirements.txt`, `.env` |

---

## 🐳 4. DOCKER : QUI TOURNE OÙ ?

| Service | Image / Commande | Port(s) | Rôle |
|---------|------------------|---------|------|
| **postgres** | postgres:15 | 5432 (interne) | BDD Airflow (métadonnées DAGs, runs, etc.). |
| **airflow-init** | apache/airflow | - | Une fois : init BDD + utilisateur admin. |
| **airflow-webserver** | apache/airflow webserver | **8080** | UI Airflow (planification, logs, trigger DAGs). |
| **airflow-scheduler** | apache/airflow scheduler | - | Exécute les tâches des DAGs. |
| **mock-api** | apache/airflow + `mock_api.py` | **8099** | API factice pour le DAG ETL (orders). |
| **invoice-web** | python:3.11-slim + Flask | **5000** | Backend + servage du frontend (web_app.py + templates). |

Réseau commun : **airflow-net**. Les conteneurs résolvent les noms (ex. `mock-api`, `postgres`).

---

## ✅ 5. CE QU’IL FAUT RETENIR

1. **Front** = `templates/index.html` (tout le code visible dans le navigateur).
2. **Back** = `web_app.py` (routes + API) + `invoice_processor.py` (traitement factures).
3. **Airflow** = `dags/*.py` ; le DAG des factures s’appelle **`projet_facture`** dans `d5_invoice_processing.py`.
4. **Pas d’appel direct Back ↔ Airflow** : ils partagent le **même module** (`invoice_processor.py`) et les **mêmes dossiers** (`uploads/`, `data/`).
5. **Changements de comportement** :
   - Modifier l’interface → éditer `templates/index.html`.
   - Modifier l’API ou la logique d’upload/export côté web → `web_app.py`.
   - Modifier la logique OCR/parsing/Excel → `invoice_processor.py` (impacte web et Airflow).
   - Modifier le workflow ou la planification des factures → `dags/d5_invoice_processing.py` (DAG `projet_facture`).

Si tu veux, on peut ajouter une section « FAQ » ou « Dépannage » à la fin de ce fichier.

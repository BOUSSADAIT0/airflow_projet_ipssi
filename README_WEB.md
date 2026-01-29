# Interface Web et Intégration Airflow - Extraction de Factures

> **📐 Architecture détaillée** : voir **[ARCHITECTURE.md](ARCHITECTURE.md)** pour l’emplacement du code front/back/Airflow et leurs interactions.

## 📋 Vue d'ensemble

Ce projet transforme l'application Tkinter d'extraction de factures en une **interface web moderne** avec intégration **Airflow** pour l'automatisation.

## 🚀 Fonctionnalités

### Interface Web (Flask)
- ✅ Upload de factures (PDF, images)
- ✅ Extraction automatique avec OCR (Ollama, Tesseract, Auto)
- ✅ Affichage des données extraites
- ✅ Export vers Excel et JSON
- ✅ Traitement par lot
- ✅ Interface moderne et responsive

### DAG Airflow
- ✅ Traitement automatique des factures toutes les heures
- ✅ Validation des données extraites
- ✅ Export automatique vers Excel
- ✅ Génération de rapports
- ✅ Gestion des erreurs et retry

## 📁 Structure des fichiers

```
.
├── web_app.py                 # Application Flask principale
├── invoice_processor.py       # Service de traitement (sans Tkinter)
├── dags/
│   └── d5_invoice_processing.py  # DAG Airflow
├── templates/
│   └── index.html             # Interface web
├── uploads/                   # Dossier pour les fichiers uploadés
├── data/                      # Dossier pour les données et Excel
└── docker-compose.yml         # Configuration Docker
```

## 🛠️ Installation et démarrage

### 1. Démarrer les services

```bash
docker compose up -d
```

### 2. Accéder aux interfaces

- **Interface Web**: http://localhost:5000
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **Mock API**: http://localhost:8099

### 3. Comment lancer Airflow (essentiel)

Airflow orchestre le traitement automatique des factures. Pour le lancer :

1. **Démarrer tous les services** (dont Airflow) :
   ```bash
   docker compose up -d
   ```
2. **Attendre que les conteneurs soient prêts** (Postgres, init, webserver, scheduler) :
   ```bash
   docker compose ps
   ```
   Vérifier que `airflow-webserver` et `airflow-scheduler` sont "Up".
3. **Ouvrir l’interface Airflow** : http://localhost:8080  
   - Identifiants : **admin** / **admin**
4. **Activer le DAG des factures** : dans la liste des DAGs, trouver **`projet_facture`** et basculer le toggle sur **ON** (activé).
5. **Déclencher une exécution** (optionnel) : cliquer sur le DAG → **Trigger DAG** (bouton play). Sinon le DAG tourne **toutes les heures** automatiquement.
6. **Déposer des factures** : placer les PDF ou images dans le dossier **`uploads/`** à la racine du projet. Au prochain run, Airflow les traitera (extraction sémantique locale par défaut, export Excel dans `data/`).

**Résumé des commandes :**
```bash
docker compose up -d              # Lancer Airflow + web + Postgres
docker compose logs airflow-scheduler   # Voir les logs du scheduler
docker compose down                # Tout arrêter
```

### 4. Utilisation

#### Via l'interface web
1. Ouvrir http://localhost:5000
2. Sélectionner ou glisser-déposer une facture
3. Choisir la méthode d'extraction (Semantic, Auto, Ollama, Tesseract)
4. Visualiser les données extraites
5. Exporter vers Excel ou JSON

#### Via Airflow
1. Accéder à http://localhost:8080 (admin / admin)
2. Activer le DAG **`projet_facture`** (fichier `dags/d5_invoice_processing.py`)
3. Le DAG s'exécute automatiquement toutes les heures (ou déclencher manuellement)
4. Placer les factures dans le dossier **`uploads/`**
5. Les factures sont traitées avec la méthode **sémantique** (locale, sans Ollama/API) et exportées dans `data/factures.xlsx`

## 🔧 Configuration

### Variables d'environnement

Créer un fichier `.env` :

```env
AIRFLOW_UID=50000
OPENAI_API_KEY=votre_clé_openai
SECRET_KEY=votre_secret_key_flask
OLLAMA_BASE_URL=http://ollama:11434
```

### Méthodes d'extraction

- **Semantic** (par défaut dans le DAG) : 100 % local (regex + spaCy optionnel), PDF texte direct ou OCR Tesseract — pas d’Ollama ni API.
- **Auto**: Utilise Ollama si disponible, sinon Tesseract
- **Ollama**: Utilise les modèles locaux Ollama (llama3.2, mistral, etc.)
- **Tesseract**: Utilise Tesseract OCR classique

## 📊 API REST

### Endpoints disponibles

- `POST /api/upload` - Uploader un fichier
- `POST /api/process` - Traiter une facture
- `POST /api/batch` - Traiter plusieurs factures
- `POST /api/export/excel` - Exporter vers Excel
- `GET /api/history` - Récupérer l'historique
- `GET /api/status` - Statut de l'application

### Exemple d'utilisation API

```bash
# Upload
curl -X POST -F "file=@facture.pdf" http://localhost:5000/api/upload

# Traitement
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/app/uploads/facture.pdf", "method": "auto"}'
```

## 🔄 Workflow Airflow

Le DAG **`projet_facture`** (`dags/d5_invoice_processing.py`) :

1. **check_invoice_files** : Vérifie s'il y a des fichiers à traiter
2. **process_all_invoices** : Traite toutes les factures trouvées
3. **validate_extracted_data** : Valide les données extraites
4. **generate_report** : Génère un rapport du traitement

## 📝 Notes importantes

- Les fichiers doivent être placés dans `uploads/` pour être traités par Airflow
- Les données extraites sont automatiquement exportées vers `data/factures.xlsx`
- Le traitement par lot est disponible via l'interface web
- Les doublons sont automatiquement détectés avant l'export Excel

## 🐛 Dépannage

### L'interface web ne démarre pas
```bash
docker compose logs invoice-web
```

### Le DAG Airflow échoue
```bash
docker compose logs airflow-scheduler
docker compose logs airflow-webserver
```
Vérifier que le dossier `uploads/` existe et que le volume projet est bien monté (`.:/opt/airflow/project` dans `docker-compose.yml`).

### Ollama non disponible
- Vérifier que Ollama est installé et démarré localement
- Ou utiliser la méthode "Tesseract" à la place

## 📚 Dépendances

- Flask
- Pillow (PIL)
- openpyxl
- requests
- Apache Airflow 2.8.1

## 🎯 Prochaines étapes

- [ ] Ajouter l'authentification utilisateur
- [ ] Implémenter les webhooks pour notifications
- [ ] Ajouter un dashboard de statistiques
- [ ] Intégrer avec une base de données pour l'historique
- [ ] Ajouter des tests unitaires

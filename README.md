# Application d’extraction de factures (Web + Airflow)

Interface web pour extraire les données des factures (PDF, images) et les exporter en Excel, avec automatisation par Airflow.

---

## Démarrer l’application

### 1. Lancer tous les services (Docker)

À la racine du projet :

```bash
docker compose up -d
```

Cela démarre :
- **Interface web** (Flask) sur le port **5000**
- **Airflow** (webserver + scheduler) sur le port **8080**
- **PostgreSQL** (base Airflow)
- Optionnel : mock API sur le port 8099

### 2. Vérifier que tout tourne

```bash
docker compose ps
```

Vérifier que `invoice-web`, `airflow-webserver` et `airflow-scheduler` sont **Up**.

### 3. Accéder à l’app

| Service        | URL                     | Identifiants   |
|----------------|-------------------------|----------------|
| **App web**    | http://localhost:5000   | —              |
| **Airflow UI** | http://localhost:8080   | **admin** / **admin** |

---

## Utilisation rapide

### Via l’interface web (http://localhost:5000)

1. **Paramètres** (en haut) : indiquer le **dossier des factures**, le **fichier Excel de sortie** et l’**intervalle du DAG** (ex. 1 h), puis cliquer sur **Enregistrer la config**.
2. **Traiter tout de suite** : cliquer sur **Traiter le dossier maintenant** pour lancer l’extraction sur le dossier configuré.
3. **Une facture à la fois** : glisser-déposer un fichier dans la zone prévue, choisir la méthode (Sémantique, Auto, Ollama, Tesseract), puis exporter en Excel ou JSON.

### Via Airflow (traitement automatique)

1. Ouvrir http://localhost:8080 et se connecter (admin / admin).
2. Activer le DAG **`projet_facture`** (toggle ON).
3. Déposer les factures dans le dossier configuré (par défaut `uploads/`). Le DAG vérifie à l’intervalle choisi (ex. 1 h) et traite les fichiers, puis met à jour l’Excel configuré.

---

## Comment vérifier si Airflow fonctionne

### 1. Vérifier que les conteneurs tournent

```bash
docker compose ps
```

Tu dois voir **airflow-webserver** et **airflow-scheduler** avec le statut **Up**. Si **airflow-init** est encore en cours, attendre qu’il termine.

### 2. Ouvrir l’interface Airflow

Ouvre dans le navigateur : **http://localhost:8080**

- **Identifiants :** admin / admin  
- Si la page s’affiche, le **webserver** fonctionne.

### 3. Vérifier que le DAG est chargé

Dans l’interface Airflow :

1. Va dans **DAGs** (menu ou liste des DAGs).
2. Cherche le DAG **`projet_facture`**.
3. Vérifie qu’il n’y a **pas d’erreur** (pas de pastille rouge « Failed » ou « Import error »).  
   - Si le DAG apparaît sans erreur, le **scheduler** charge bien ton DAG.

### 4. Activer et lancer le DAG

1. Passe le **toggle** du DAG **`projet_facture`** sur **ON** (activé).
2. Clique sur le nom du DAG **`projet_facture`** pour ouvrir le détail.
3. Clique sur **Trigger DAG** (bouton play ▶).
4. Va dans **Runs** (ou **Grid** / **Graph**) : une nouvelle exécution doit apparaître et les tâches doivent passer en vert au fur et à mesure.

### 5. Consulter les logs en cas de problème

```bash
docker compose logs airflow-scheduler
docker compose logs airflow-webserver
```

Pour suivre les logs en direct :

```bash
docker compose logs -f airflow-scheduler
```

**En résumé :** Airflow fonctionne si (1) les conteneurs sont Up, (2) l’UI s’ouvre sur http://localhost:8080, (3) le DAG `projet_facture` est visible sans erreur, et (4) un run déclenché manuellement s’exécute (tâches vertes).

---

## Commandes utiles

```bash
docker compose up -d              # Démarrer l’app
docker compose down              # Tout arrêter
docker compose logs invoice-web  # Logs de l’interface web
docker compose logs airflow-scheduler  # Logs du DAG
```

---

## Structure du projet

- **`web_app.py`** — Application Flask (interface web)
- **`invoice_processor.py`** — Traitement des factures (OCR, extraction sémantique)
- **`semantic_extractor.py`** — Extraction locale (regex + spaCy)
- **`user_config.py`** — Config utilisateur (dossier, Excel, intervalle DAG)
- **`dags/d5_invoice_processing.py`** — DAG Airflow `projet_facture`
- **`uploads/`** — Dossier des factures (par défaut)
- **`data/`** — Fichiers Excel, rapports, config

Pour plus de détails (API, dépannage, architecture), voir **README_WEB.md**.

# OCR Intelligent – Présentation technique

Document pour la présentation : utilisation du DAG Airflow, tâches, modèle d’extraction.

---

## 1. Utilisation du DAG Airflow

- **Nom du DAG :** `ocr_batch_pipeline`
- **Rôle :** Traiter automatiquement les fichiers déposés dans l’inbox (upload via l’app ou dépôt manuel) en les envoyant à l’API OCR du backend.
- **Déclenchement :** Le DAG est planifié **toutes les 1 minute** (`schedule_interval=timedelta(minutes=1)`). Dès qu’au moins un fichier (PDF ou image) est présent dans le dossier inbox, le sensor se débloque et le pipeline s’exécute.
- **Variables Airflow (optionnelles) :** `ocr_api_url`, `ocr_inbox_path`, `ocr_username`, `ocr_password` (Admin > Variables).

---

## 2. Nombre de tâches et rôle de chacune

Il y a **7 types de tâches** (certaines peuvent être exécutées plusieurs fois) :

| # | Tâche | Type | Rôle |
|---|--------|------|------|
| 1 | **start** | EmptyOperator | Marque le début du DAG. |
| 2 | **wait_for_file** | PythonSensor | Attend qu’au moins un fichier (PDF, PNG, JPG, etc.) soit présent dans `/opt/airflow/inbox`. Vérifie toutes les **30 secondes**, timeout **1 heure**. |
| 3 | **get_token_task** | @task | Récupère un **token JWT** auprès du backend (`POST /api/auth/login`) pour appeler l’API OCR. |
| 4 | **list_files_task** | @task | Liste les **chemins des fichiers** à traiter dans l’inbox (hors dossier `processed/`). |
| 5 | **process_file_task** | @task (×N) | **Une tâche par fichier.** Pour chaque fichier : envoie le fichier au backend (`POST /api/ocr/extract`), récupère le résultat, puis **déplace le fichier** vers `inbox/processed/` pour ne pas le retraiter. |
| 6 | **resume_task** | @task | Fait un **résumé** du run (nombre de fichiers traités, liste des résultats). |
| 7 | **end** | EmptyOperator | Marque la fin du DAG. |

**Ordre du flux :**  
`start` → `wait_for_file` → `get_token_task` et `list_files_task` (en parallèle) → `process_file_task` (×N, un par fichier) → `resume_task` → `end`.

---

## 3. Modèle / moteur d’extraction (OCR + structuration)

L’extraction est faite **côté backend** (API `/api/ocr/extract`), pas dans Airflow. Le DAG ne fait qu’envoyer les fichiers à cette API.

### 3.1 Moteur OCR

- **Bibliothèque :** **Tesseract** (via **pytesseract**).
- **Langues :** français + anglais (`fra+eng` par défaut, configurable).
- **Formats :** PDF (converti en images avec **pdf2image**), images (PNG, JPG, etc.), et `.pages`.

### 3.2 Préprocessing des images

- **Fichier :** `backend/app/services/image_processing.py` – fonction `preprocess_image()`.
- **Étapes :**
  1. Conversion en **niveaux de gris** (OpenCV).
  2. **Redimensionnement** si l’image est trop petite (hauteur ou largeur < 1000 px).
  3. **Dilatation / érosion** pour réduire le bruit.
  4. **Seuillage adaptatif** (Gaussian) pour obtenir une image binaire (noir/blanc) et mieux gérer la lumière.
- **Fallback :** Si le préprocessing échoue, l’image originale est utilisée pour Tesseract.

### 3.3 Détection du type de document

- **Fichier :** `backend/app/main_simple.py` – fonction `detect_document_type(text, filename)`.
- **Méthode :** Mots-clés dans le **texte** (et le nom de fichier) :
  - **Facture :** facture, invoice, montant, total, tva, ttc → `invoice`
  - **CV :** cv, curriculum, expérience, compétence, education, skills → `cv`
  - **Exercice :** exercice, question, réponse, devoir, homework → `exercise`
  - **Dissertation :** essay, dissertation, thèse, introduction, conclusion, tpe → `essay`
  - **Contrat :** contrat, contract, agreement, signature → `contract`
- **Par défaut :** `document` si aucun mot-clé ne correspond.

### 3.4 Extraction structurée

- **Fichier :** `backend/app/services/extraction.py` – fonction `extract_structured_data(text, doc_type)`.
- **Selon le type de document :**
  - **CV (`extract_cv_info`) :** nom, email, téléphone, adresse, compétences, formation, expérience (sections détectées par mots-clés : Compétences, Formation, Expérience, etc.).
  - **Facture (`extract_invoice_info`) :** numéro de facture, dates, montants, TVA, fournisseur, client, etc. (regex + motifs).
  - **Autres :** extraction générique (emails, téléphones via regex).
- **Techniques :** **Regex** (emails, téléphones FR/internationaux, montants, dates), **heuristiques** (sections CV, lignes courtes pour en-têtes), **pas de modèle de ML** (pas de SpaCy/transformer dans le flux principal utilisé par le DAG).

---

## 4. Résumé en une phrase

**Le DAG Airflow surveille l’inbox toutes les minutes, attend un fichier (sensor), récupère un token, liste les fichiers, envoie chaque fichier au backend qui fait l’OCR (Tesseract + préprocessing OpenCV), détecte le type de document (mots-clés) et extrait des champs structurés (regex + heuristiques) ; les résultats sont stockés dans `results/` et affichés dans le frontend.**

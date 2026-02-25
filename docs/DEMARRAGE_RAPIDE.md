# Démarrage rapide – Voir Frontend, Backend, Airflow et HDFS

## Prérequis

- **Docker** et **Docker Compose** installés sur ta machine.
- Terminal dans le dossier du projet : `airflow_projet_ipssi`.

---

## 1. Lancer tout le projet

Dans le dossier du projet, exécute :

```bash
cd /home/sondes/airflow_projet_ipssi
docker-compose up -d
```

La première fois, le build des images peut prendre quelques minutes. Attends que tous les conteneurs soient « Up ».

Vérifier que tout tourne :

```bash
docker-compose ps
```

Tu dois voir : `backend`, `frontend`, `airflow`, `airflow-db`, `hadoop-namenode`, `hadoop-datanode` en état **Up**.

---

## 2. Tout voir depuis le Frontend (présentation projet)

L’interface web regroupe **OCR**, **Data Lake / HDFS** et **Analytics** :

- **http://localhost** (accueil) : liens « Data Lake / HDFS » et « Tableau de bord Analytics ».
- **Data Lake** : structure des zones raw / clean / curated, dépôt de fichiers CSV/JSON vers le Data Lake, lien vers l’interface HDFS (9870).
- **Analytics** : indicateurs (total factures, montants TTC/HT), graphiques par région, pays et mode de paiement (données curated).

Aucune connexion n’est requise pour ouvrir les pages Data Lake et Analytics depuis l’accueil.

---

## 3. Où voir chaque partie (technique) ?

| Partie      | URL dans le navigateur      | Ce que tu vois |
|------------|-----------------------------|-----------------|
| **Frontend** | **http://localhost**        | Interface web (upload de documents, historique, résultats). |
| **Backend**  | **http://localhost:8000**    | API (page d’accueil JSON). |
| **Backend (docs)** | **http://localhost:8000/docs** | Documentation Swagger de l’API. |
| **Airflow**  | **http://localhost:8080**   | Interface Airflow (DAGs, exécutions). |
| **HDFS (NameNode)** | **http://localhost:9870** | Interface Web HDFS (fichiers sur le cluster). |

### Connexion Airflow

- **URL** : http://localhost:8080  
- **Identifiant** : `admin`  
- **Mot de passe** : `admin`  

(au premier lancement, la création du compte peut prendre 1–2 minutes ; rafraîchis la page si « Unauthorized ».)

---

## 4. Voir les données HDFS

### Option A : Dossier local (le plus simple)

Les données écrites par les DAGs sont dans le dossier **`hdfs`** à la racine du projet :

```
airflow_projet_ipssi/
  hdfs/
    raw/factures/files/   → factures source "fichiers"
    raw/factures/db/      → factures source "base de données"
    raw/factures/api/     → factures source "API"
    clean/factures/api/   → factures enrichies (API)
    curated/analytics/   → agrégations (après DAG batch_analytics_factures)
```

Tu peux ouvrir ces dossiers dans ton explorateur de fichiers ou dans l’IDE. Les fichiers apparaissent après l’exécution des DAGs (voir ci‑dessous).

### Option B : Interface Web HDFS (NameNode)

1. Ouvre **http://localhost:9870** dans le navigateur.
2. Menu **Utilities** → **Browse the file system**.
3. Tu verras le système de fichiers HDFS du cluster (ex. `/`). Les données du projet sont sous **`/datalake/`** (raw, clean, curated).

**Pourquoi le datalake est vide (size 0) ?**  
Les DAGs écrivent d’abord dans le dossier local **`./hdfs`**. L’upload vers le cluster HDFS via WebHDFS peut échouer (redirection DataNode, délai de démarrage du cluster). Du coup, l’interface HDFS affiche un datalake vide alors que **`./hdfs`** contient bien les fichiers.

**Solution : remplir le datalake depuis le dossier local** (une fois les DAGs exécutés) :

```bash
# À la racine du projet
chmod +x scripts/sync_hdfs_to_datalake.sh
./scripts/sync_hdfs_to_datalake.sh
```

Cela copie le contenu de **`./hdfs`** (vu par le NameNode comme `/data`) vers **`/datalake`** sur le cluster. Ensuite, sur http://localhost:9870 → Browse the file system → **/datalake**, tu verras raw, clean et curated.

---

## 5. Déclencher les DAGs pour remplir HDFS

1. Va sur **http://localhost:8080** et connecte-toi (admin / admin).
2. Dans la liste des DAGs :
   - **multi_source_ingestion_factures** : ingestion des 3 sources (fichiers, DB, API) + enrichissement → remplit `raw/` et `clean/`.
   - **batch_analytics_factures** : agrégations → remplit `curated/`.
3. À gauche du nom du DAG, active le **toggle** (Off → On).
4. Clique sur le nom du DAG, puis sur le bouton **« Trigger DAG »** (icône play) pour lancer une exécution.

Quelques minutes après, vérifie le dossier **`hdfs/`** (ou l’interface HDFS) : les fichiers du jour (date du jour en `YYYY-MM-DD`) apparaissent.

---

## 6. Récapitulatif des URLs

```
Frontend (interface utilisateur) :  http://localhost
Backend (API)                      :  http://localhost:8000
Backend (documentation API)         :  http://localhost:8000/docs
Airflow (orchestration)             :  http://localhost:8080   (admin / admin)
HDFS NameNode (fichiers cluster)    :  http://localhost:9870
Données locales (HDFS simulé)      :  dossier ./hdfs dans le projet
```

---

## 7. (Optionnel) Stack Big Data : Kafka + Prometheus + Grafana

Si tu veux en plus Kafka, Prometheus et Grafana :

```bash
docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml up -d
```

Puis :

- **Grafana** : http://localhost:3000 (admin / admin)
- **Prometheus** : http://localhost:9090

---

## 8. Arrêter le projet

```bash
docker-compose down
```

Pour tout arrêter **et** supprimer les volumes (bases de données, logs, etc.) :

```bash
docker-compose down -v
```

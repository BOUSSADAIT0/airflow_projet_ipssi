# Projet Big Data – Guide de déploiement et d’utilisation

Ce document décrit comment lancer et utiliser l’architecture Big Data du projet (ingestion multi-sources, batch, temps réel, stockage distribué, analytics, monitoring).

## Prérequis

- Docker et Docker Compose
- Pour Kafka + monitoring : `docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml`

## 1. Lancer le projet (base)

```bash
docker-compose up -d
```

- **Frontend** : http://localhost  
- **Backend** : http://localhost:8000  
- **Airflow** : http://localhost:8080 (admin / admin)  
- **HDFS NameNode UI** : http://localhost:9870  

## 2. Lancer la stack Big Data (Kafka + monitoring)

```bash
docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml up -d
```

Services supplémentaires :

- **Kafka** : `localhost:9092` (bootstrap)  
- **Prometheus** : http://localhost:9090  
- **Grafana** : http://localhost:3000 (admin / admin)  
- **Consumer Kafka** : écrit dans `hdfs/streaming/<date>/`  

### Variables Airflow pour Kafka (optionnel)

Dans Airflow > Admin > Variables, ajouter :

- **Clé** : `kafka_bootstrap_servers`  
- **Valeur** : `kafka:29092`  

Après un run du DAG `multi_source_ingestion_factures`, la tâche `publish_enriched_to_kafka` enverra les factures enrichies vers le topic `factures-enriched`. Le consumer les écrira dans `hdfs/streaming/`.

Pour que le producer Kafka fonctionne dans Airflow, installer `kafka-python` dans l’image Airflow (Dockerfile personnalisé ou pip dans le conteneur).

## 3. DAGs Airflow

| DAG | Rôle | Schedule |
|-----|------|----------|
| **multi_source_ingestion_factures** | Ingestion fichiers + DB + API, enrichissement, upload HDFS, option Kafka | @daily |
| **batch_analytics_factures** | Agrégations (pays, région, mode paiement) → zone curated | Toutes les heures |
| **ocr_batch_pipeline** | Sensor inbox → API OCR → traitement des documents | Toutes les 1 min |

Les trois sources d’ingestion (files, db, api) s’exécutent **en parallèle** ; l’enrichissement API et la publication Kafka s’exécutent après.

## 4. Stockage (Data Lake)

- **Local** (volume `./hdfs`) :  
  - `raw/factures/{files|db|api}/<date>/`  
  - `clean/factures/api/<date>/`  
  - `curated/analytics/<date>/`  
  - `streaming/<date>/` (si consumer Kafka actif)  

- **Cluster HDFS** (WebHDFS) : mêmes chemins sous `/datalake/`.

**Si l’interface HDFS (http://localhost:9870) affiche un datalake vide (size 0)** : les DAGs écrivent d’abord dans `./hdfs` ; l’upload WebHDFS depuis Airflow peut échouer (redirection DataNode, délai de démarrage). Remplis le datalake depuis le dossier local avec :

```bash
./scripts/sync_hdfs_to_datalake.sh
```

## 5. Exposition analytique

Le backend expose une API Analytics (données curated) :

- **GET /api/analytics/summary** : résumé global (total factures, montants, par pays/région/paiement).  
- **GET /api/analytics/by_region** : agrégats par région.  
- **GET /api/analytics/by_country** : agrégats par pays.  
- **GET /api/analytics/dates** : liste des dates disponibles.  

Paramètre optionnel : `?date=YYYY-MM-DD` pour une date donnée.

Le volume `./hdfs/curated` est monté en lecture seule dans le backend (`/app/data/curated`).

## 6. Monitoring

- **Prometheus** : scrape du backend (`/metrics`, `/health`) et de Prometheus.  
- **Grafana** : datasource Prometheus pré-provisionnée ; dashboard « Big Data Pipeline - Overview ».  

Pour des alertes sur échec de DAG : configurer des règles dans Prometheus (ex. si vous exposez les métriques Airflow) ou utiliser les alertes Grafana sur les métriques disponibles.

## 7. Architecture détaillée

Voir [ARCHITECTURE_BIG_DATA.md](ARCHITECTURE_BIG_DATA.md) pour le schéma complet et les composants (ingestion multi-sources, batch, temps réel, stockage, analytics, monitoring).

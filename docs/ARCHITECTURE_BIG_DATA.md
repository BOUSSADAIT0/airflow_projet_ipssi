# Architecture Big Data – Projet IPSSI

Ce document décrit l’architecture Big Data mise en place pour faire évoluer le projet (OCR + ingestion factures) vers une **pipeline d’ingestion robuste et scalable**, avec traitement batch et temps réel, stockage distribué, exposition analytique et monitoring.

---

## 1. Vue d’ensemble

L’architecture vise à couvrir les cinq axes demandés :

| Axe | Description | Composants |
|-----|-------------|------------|
| **Ingestion multi-sources** | Fichiers, base de données, API externes | DAG Airflow `multi_source_ingestion_factures`, Kafka (optionnel) |
| **Traitement batch et temps réel** | Batch quotidien + flux continu | DAG batch (aggregations), Kafka Producer/Consumer |
| **Stockage distribué** | Data Lake Raw / Clean / Curated | HDFS (local simulé + cluster Hadoop), WebHDFS |
| **Exposition analytique** | Requêtes et tableaux de bord | API Analytics, fichiers curated (JSON/Parquet-ready) |
| **Monitoring complet** | Métriques, dashboards, alertes | Prometheus, Grafana, alertes sur échecs DAG |

---

## 2. Schéma de l’architecture

```
                    ┌─────────────────────────────────────────────────────────────────────────┐
                    │                         SOURCES DE DONNÉES                               │
                    └─────────────────────────────────────────────────────────────────────────┘
                      │                    │                    │                    │
                      ▼                    ▼                    ▼                    ▼
              ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
              │   Fichiers   │    │   Base SQL   │    │  API (Faker  │    │  OCR (docs   │
              │  CSV / JSON  │    │  (export)   │    │  + Countries)│    │  déposés)    │
              └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
                     │                   │                   │                   │
                     └───────────────────┼───────────────────┼───────────────────┘
                                         │                   │
                    ┌────────────────────▼───────────────────▼────────────────────────────┐
                    │              ORCHESTRATION – APACHE AIRFLOW                            │
                    │  • multi_source_ingestion_factures (daily)                            │
                    │  • batch_analytics_factures (after ingestion)                          │
                    │  • ocr_batch_pipeline (sensor + API OCR)                              │
                    │  • (optionnel) kafka_producer_factures                                 │
                    └────────────────────┬───────────────────┬─────────────────────────────┘
                                         │                   │
              ┌──────────────────────────┼───────────────────┼──────────────────────────┐
              │                          ▼                   ▼                          │
              │  ┌─────────────────────────────────────────────────────────────────┐   │
              │  │              MESSAGE STREAM – KAFKA (temps réel)                  │   │
              │  │  Topic: factures-raw  →  Consumer  →  hdfs/streaming/ ou clean   │   │
              │  └─────────────────────────────────────────────────────────────────┘   │
              │                          │                                              │
              │  STOCKAGE DISTRIBUÉ       ▼                                              │
              │  ┌─────────────────────────────────────────────────────────────────┐   │
              │  │  DATA LAKE (HDFS local + cluster WebHDFS)                        │   │
              │  │  /raw/factures/{source}/{date}/   – données brutes                │   │
              │  │  /clean/factures/api/{date}/     – données enrichies (pays…)    │   │
              │  │  /curated/analytics/{date}/      – agrégations (par pays, région)│   │
              │  │  /streaming/                     – flux Kafka (optionnel)        │   │
              │  └─────────────────────────────────────────────────────────────────┘   │
              │                          │                                              │
              └──────────────────────────┼──────────────────────────────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────────────────────────────────┐
                    │                    EXPOSITION ANALYTIQUE                             │
                    │  • API Analytics (GET /analytics/summary, /by_region, etc.)           │
                    │  • Fichiers curated (JSON) pour BI / Spark / Presto                  │
                    └─────────────────────────────────────────────────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────────────────────────────┐
                    │                    MONITORING                                        │
                    │  Prometheus (métriques)  →  Grafana (dashboards)  →  Alerting        │
                    │  • DAG runs / task duration  • HDFS / Kafka health  • Alertes échec  │
                    └─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ingestion multi-sources

- **Fichiers** : écriture CSV + JSON dans `hdfs/raw/factures/files/<date>/` (génération factices pour le POC).
- **Base de données** : simulation d’un export SQL en CSV vers `hdfs/raw/factures/db/<date>/`.
- **API** : FakerAPI (produits) → mapping en factures → `hdfs/raw/factures/api/<date>/` ; enrichissement via REST Countries → `hdfs/clean/factures/api/<date>/`.
- **OCR** : dépôt de documents dans l’inbox → DAG `ocr_batch_pipeline` → API backend → résultats dans `results/`.

Les tâches d’ingestion **fichiers**, **db** et **api** peuvent être exécutées **en parallèle** ; l’enrichissement API s’exécute après la source API. Une option **Kafka** permet de publier les factures (ex. API) vers un topic pour le flux temps réel.

---

## 4. Traitement batch et temps réel

### 4.1 Batch

- **DAG `multi_source_ingestion_factures`** : ingestion quotidienne vers Raw puis Clean (enrichissement).
- **DAG `batch_analytics_factures`** : lit les données **clean** (factures enrichies), calcule des agrégations (par pays, région, montants), écrit dans **curated** (`hdfs/curated/analytics/<date>/`). Peut être déclenché après l’ingestion (downstream).

### 4.2 Temps réel

- **Kafka** : topic `factures-raw` (ou similaire). Un **producer** (tâche optionnelle dans le DAG ou script) envoie les factures vers Kafka.
- **Consumer** : processus (script Python ou service) qui consomme le topic et écrit dans HDFS (ex. `streaming/`) ou dans la même zone clean pour cohérence. Permet d’alimenter un flux temps réel en plus du batch.

---

## 5. Stockage distribué (Data Lake)

- **Local (volume Docker)** : `./hdfs` monté dans Airflow et optionnellement dans le namenode, avec la même arborescence.
- **Cluster HDFS** : WebHDFS (namenode:9870), base `/datalake`. Les mêmes chemins sont utilisés :
  - `/datalake/raw/factures/{source}/{date}/`
  - `/datalake/clean/factures/api/{date}/`
  - `/datalake/curated/analytics/{date}/`

Stratégie : **écriture locale systématique** ; **upload WebHDFS** avec retries pour rendre le stockage distribué fiable. En production, on peut inverser (HDFS primaire, local en cache).

---

## 6. Exposition analytique

- **Fichiers curated** : agrégations en JSON (par jour) dans `hdfs/curated/analytics/<date>/` (et équivalent HDFS cluster). Utilisables par Spark, Presto, ou tout outil BI.
- **API Analytics** : service (FastAPI) exposant par exemple :
  - `GET /analytics/summary` : résumé global (nombre factures, montants).
  - `GET /analytics/by_region` : agrégats par région.
  - `GET /analytics/by_country` : agrégats par pays.

L’API lit les fichiers curated (ou la base si on ajoute un stockage relationnel plus tard).

---

## 7. Monitoring complet

- **Prometheus** : scrape des métriques (Airflow si exposées, Kafka, HDFS/namenode si disponibles, backend/API).
- **Grafana** : dashboards pour :
  - Exécutions et durées des DAGs/tâches Airflow,
  - Santé Kafka (broker, consumer lag),
  - Santé HDFS (optionnel),
  - Métriques API (requêtes, erreurs).
- **Alerting** : règles Prometheus/Alertmanager ou Grafana pour alerter en cas d’échec critique (ex. DAG d’ingestion ou d’analytics en échec).

---

## 8. Déploiement

- **Compose principal** : `docker-compose up -d` lance backend, frontend, Airflow, Postgres, HDFS (namenode, datanode).
- **Stack Big Data + monitoring** : `docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml up -d` ajoute Kafka, Zookeeper, Prometheus, Grafana (et optionnellement le consumer Kafka).
- **Variables Airflow** : configurer `ocr_api_url`, `ocr_inbox_path`, `ocr_username`, `ocr_password` ; optionnellement les endpoints Kafka et WebHDFS si différents du défaut.

---

## 9. Récapitulatif – Réponse au cahier des charges académique

| Exigence | Réalisation dans le projet |
|----------|----------------------------|
| **Ingestion multi-sources** | DAG `multi_source_ingestion_factures` : 3 sources (fichiers CSV/JSON, base simulée, API FakerAPI) ingérées **en parallèle** vers la zone Raw ; enrichissement API (REST Countries) vers Clean. |
| **Traitement batch** | DAG `batch_analytics_factures` : lecture des données clean, agrégations (pays, région, mode de paiement), écriture en zone Curated. DAG quotidien d’ingestion. |
| **Traitement temps réel** | Kafka (topic `factures-enriched`) : producer dans le DAG d’ingestion (optionnel) ; consumer dédié qui écrit dans `hdfs/streaming/<date>/`. |
| **Stockage distribué** | HDFS local (volume `./hdfs`) + cluster Hadoop (WebHDFS) avec structure Data Lake : Raw / Clean / Curated / Streaming. Upload WebHDFS avec retries. |
| **Exposition analytique** | API FastAPI `/api/analytics/*` (summary, by_region, by_country, dates) lisant les fichiers curated ; fichiers JSON curated utilisables par BI/Spark. |
| **Monitoring complet** | Prometheus (métriques backend, scrape), Grafana (datasource + dashboard « Big Data Pipeline »), règles d’alerte (ex. BackendDown) dans `prometheus_alerts.yml`. |

Cette architecture répond aux objectifs académiques : **ingestion multi-sources**, **traitement batch et temps réel**, **stockage distribué**, **exposition analytique** et **monitoring complet**, tout en restant déployable sur une machine avec Docker.

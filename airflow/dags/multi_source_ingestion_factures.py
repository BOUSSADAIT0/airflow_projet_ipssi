from datetime import datetime
import os
import csv
import json
from random import randint, choice, uniform

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

# "HDFS" simulé dans le conteneur Airflow (monté depuis ./hdfs sur la machine hôte)
HDFS_BASE = "/opt/airflow/hdfs"
RAW_BASE = os.path.join(HDFS_BASE, "raw", "factures")
CLEAN_BASE = os.path.join(HDFS_BASE, "clean", "factures")

# HDFS distribué (cluster Hadoop via WebHDFS)
WEBHDFS_BASE = "http://hadoop-namenode:9870/webhdfs/v1"
HDFS_CLUSTER_BASE = "/datalake"

PAYS_LIST = ["FR", "DE", "ES", "IT"]
MODES_PAIEMENT = ["CB", "VIREMENT", "PAYPAL", "CHEQUE"]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_fake_invoices(n: int = 20) -> list[dict]:
    rows: list[dict] = []
    for i in range(1, n + 1):
        rows.append(
            {
                "id_facture": i,
                "date_facture": datetime.now().strftime("%Y-%m-%d"),
                "id_client": randint(1, 10),
                "montant_ht": round(uniform(10, 500), 2),
                "montant_ttc": round(uniform(10, 500) * 1.2, 2),
                "pays": choice(PAYS_LIST),
                "mode_paiement": choice(MODES_PAIEMENT),
            }
        )
    return rows


def _ensure_hdfs_dir(hdfs_path: str) -> None:
    """
    Crée un répertoire sur le cluster HDFS via WebHDFS (si besoin).
    Exemple de hdfs_path : /datalake/raw/factures/api/2026-02-25
    """
    resp = requests.put(
        f"{WEBHDFS_BASE}{hdfs_path}",
        params={"op": "MKDIRS", "user.name": "hdfs"},
        timeout=30,
    )
    resp.raise_for_status()


def _upload_file_to_hdfs(local_path: str, hdfs_path: str, max_retries: int = 3) -> None:
    """
    Envoie un fichier local vers le cluster HDFS en utilisant WebHDFS (avec retries).
    hdfs_path est un chemin absolu HDFS, par ex. /datalake/raw/factures/api/2026-02-25/file.json
    """
    import time
    last_error = None
    for attempt in range(max_retries):
        try:
            parent_dir = os.path.dirname(hdfs_path)
            _ensure_hdfs_dir(parent_dir)
            create_resp = requests.put(
                f"{WEBHDFS_BASE}{hdfs_path}",
                params={"op": "CREATE", "overwrite": "true", "user.name": "hdfs"},
                allow_redirects=False,
                timeout=30,
            )
            create_resp.raise_for_status()
            location = create_resp.headers.get("Location")
            if not location:
                raise RuntimeError("Pas d'en-tête Location retourné par WebHDFS pour l'upload.")
            with open(local_path, "rb") as f:
                data_resp = requests.put(location, data=f, timeout=60)
            data_resp.raise_for_status()
            return
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise last_error


def ingest_from_files(**context):
    """Simule une source 'fichiers' en écrivant CSV + JSON dans le HDFS simulé."""
    today = datetime.now().strftime("%Y-%m-%d")
    target_dir = os.path.join(RAW_BASE, "files", today)
    _ensure_dir(target_dir)

    rows = generate_fake_invoices(20)

    csv_path = os.path.join(target_dir, f"factures_files_{today}.csv")
    json_path = os.path.join(target_dir, f"factures_files_{today}.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    return {
        "csv_path": csv_path,
        "json_path": json_path,
        "count": len(rows),
    }


def ingest_from_db(**context):
    """
    Simule une source 'base de données' :
    on considère qu'une requête SQL a été faite et on écrit le résultat en CSV dans le HDFS simulé.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    target_dir = os.path.join(RAW_BASE, "db", today)
    _ensure_dir(target_dir)

    rows = generate_fake_invoices(15)

    csv_path = os.path.join(target_dir, f"factures_db_{today}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return {
        "csv_path": csv_path,
        "count": len(rows),
    }


def ingest_from_api(**context):
    """
    Utilise une API de test publique (FakerAPI) pour récupérer des données
    et les transformer en factures factices, puis les stocker dans le HDFS simulé.
    Ici on consomme l'endpoint Products comme source externe.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    target_dir = os.path.join(RAW_BASE, "api", today)
    _ensure_dir(target_dir)

    api_url = "https://fakerapi.it/api/v2/products"
    # On demande 100 produits en français, qu'on va mapper en "lignes de facture"
    resp = requests.get(
        api_url,
        params={
            "_quantity": 1000,
            "_locale": "fr_FR",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    products = payload.get("data", [])

    # Mapping simple produit -> "facture" (chaque produit = 1 facture pour le POC)
    rows = []
    for idx, p in enumerate(products, start=1):
        price = float(p.get("price", 0))
        rows.append(
            {
                "id_facture": idx,
                "date_facture": today,
                "id_client": randint(1, 10),
                "montant_ht": round(price, 2),
                "montant_ttc": round(price * 1.2, 2),
                "pays": choice(PAYS_LIST),
                "mode_paiement": choice(MODES_PAIEMENT),
                "produit_nom": p.get("name"),
                "produit_description": p.get("description"),
                "produit_code": p.get("ean"),
            }
        )

    json_path = os.path.join(target_dir, f"factures_api_{today}.json")

    # Écriture dans le "HDFS" local (volume Docker) pour consultation rapide
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    # Tentative optionnelle d'écriture dans le HDFS distribué via WebHDFS
    hdfs_target = f"{HDFS_CLUSTER_BASE}/raw/factures/api/{today}/factures_api_{today}.json"
    try:
        _upload_file_to_hdfs(json_path, hdfs_target)
        hdfs_status = "uploaded"
    except Exception as e:
        # On log l'erreur mais on ne fait pas échouer la tâche
        print(f"[WARN] Impossible d'uploader vers HDFS distribué: {e}")
        hdfs_status = "error"

    return {
        "json_path": json_path,
        "hdfs_path": hdfs_target,
        "hdfs_status": hdfs_status,
        "count": len(rows),
    }


def enrich_api_invoices_with_country(**context):
    """
    Enrichit les factures issues de l'API FakerAPI avec des informations pays
    provenant d'une deuxième API publique (REST Countries).

    - Source : hdfs/raw/factures/api/<date>/factures_api_<date>.json
    - Cible  : hdfs/clean/factures/api/<date>/factures_api_enriched_<date>.json
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Chemin du fichier brut issu de l'API FakerAPI
    raw_dir = os.path.join(RAW_BASE, "api", today)
    raw_path = os.path.join(raw_dir, f"factures_api_{today}.json")

    if not os.path.exists(raw_path):
        # Rien à enrichir
        return {"status": "no_raw_file"}

    with open(raw_path, "r", encoding="utf-8") as f:
        invoices = json.load(f)

    # Deuxième API : REST Countries (pas d'auth, données pays)
    # On récupère uniquement les pays présents dans les factures
    distinct_countries = sorted({inv.get("pays") for inv in invoices if inv.get("pays")})
    codes_param = ",".join(distinct_countries)

    restcountries_url = "https://restcountries.com/v3.1/alpha"
    resp = requests.get(
        restcountries_url,
        params={
            "codes": codes_param,
            "fields": "cca2,region,subregion,currencies",
        },
        timeout=30,
    )
    resp.raise_for_status()
    countries_payload = resp.json()

    # Construction d'un mapping code pays -> infos enrichies
    country_map: dict[str, dict] = {}
    for c in countries_payload:
        code = c.get("cca2")
        if not code:
            continue
        region = c.get("region")
        subregion = c.get("subregion")
        currencies = c.get("currencies") or {}
        # On prend la première monnaie du dict
        currency_code = None
        currency_name = None
        if currencies:
            first_code, first_val = next(iter(currencies.items()))
            currency_code = first_code
            currency_name = (first_val or {}).get("name")

        country_map[code] = {
            "country_region": region,
            "country_subregion": subregion,
            "currency_code": currency_code,
            "currency_name": currency_name,
        }

    # Enrichissement des factures
    enriched = []
    for inv in invoices:
        code = inv.get("pays")
        extra = country_map.get(code, {})
        enriched_inv = {
            **inv,
            **extra,
        }
        enriched.append(enriched_inv)

    # Écriture dans la zone "clean"
    clean_dir = os.path.join(CLEAN_BASE, "api", today)
    _ensure_dir(clean_dir)
    clean_path = os.path.join(clean_dir, f"factures_api_enriched_{today}.json")

    # Écriture en zone "clean" locale (volume Docker)
    with open(clean_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    # Écriture en zone "clean" sur le cluster HDFS (best-effort)
    hdfs_clean_target = f"{HDFS_CLUSTER_BASE}/clean/factures/api/{today}/factures_api_enriched_{today}.json"
    try:
        _upload_file_to_hdfs(clean_path, hdfs_clean_target)
        hdfs_status = "uploaded"
    except Exception as e:
        print(f"[WARN] Impossible d'uploader le clean vers HDFS distribué: {e}")
        hdfs_status = "error"

    return {
        "input_path": raw_path,
        "output_path": clean_path,
        "hdfs_clean_path": hdfs_clean_target,
        "hdfs_status": hdfs_status,
        "input_count": len(invoices),
        "output_count": len(enriched),
    }


def publish_enriched_to_kafka(**context):
    """
    Publie les factures enrichies vers Kafka (topic factures-enriched) pour le flux temps réel.
    Optionnel : ne fait rien si Kafka n'est pas configuré (variable kafka_bootstrap_servers vide).
    """
    try:
        from airflow.models import Variable
        bootstrap = Variable.get("kafka_bootstrap_servers", default_var="")
        if not bootstrap:
            return {"status": "skipped", "reason": "kafka_bootstrap_servers non configuré"}
    except Exception:
        return {"status": "skipped", "reason": "Variable non disponible"}

    try:
        from kafka import KafkaProducer
    except ImportError:
        return {"status": "skipped", "reason": "kafka-python non installé"}

    today = datetime.now().strftime("%Y-%m-%d")
    clean_path = os.path.join(CLEAN_BASE, "api", today, f"factures_api_enriched_{today}.json")
    if not os.path.exists(clean_path):
        return {"status": "skipped", "reason": "fichier clean absent"}

    with open(clean_path, "r", encoding="utf-8") as f:
        enriched = json.load(f)

    producer = KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )
    topic = "factures-enriched"
    sent = 0
    for inv in enriched:
        producer.send(topic, value=inv)
        sent += 1
    producer.flush()
    producer.close()
    return {"status": "ok", "topic": topic, "sent": sent}


default_args = {
    "owner": "data-engineer",
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id="multi_source_ingestion_factures",
    default_args=default_args,
    description="Ingestion multi-sources (files, db, api) de factures vers un HDFS simulé",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["factures", "ingestion", "multi-source"],
) as dag:
    ingest_files_task = PythonOperator(
        task_id="ingest_from_files",
        python_callable=ingest_from_files,
    )

    ingest_db_task = PythonOperator(
        task_id="ingest_from_db",
        python_callable=ingest_from_db,
    )

    ingest_api_task = PythonOperator(
        task_id="ingest_from_api",
        python_callable=ingest_from_api,
    )

    enrich_api_task = PythonOperator(
        task_id="enrich_api_invoices_with_country",
        python_callable=enrich_api_invoices_with_country,
    )

    publish_kafka_task = PythonOperator(
        task_id="publish_enriched_to_kafka",
        python_callable=publish_enriched_to_kafka,
    )

    # Ingestion multi-sources en parallèle ; enrichissement API après la source API
    [ingest_files_task, ingest_db_task, ingest_api_task] >> enrich_api_task
    enrich_api_task >> publish_kafka_task


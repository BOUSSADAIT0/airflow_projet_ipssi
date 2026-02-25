"""
DAG Airflow - Traitement batch analytique des factures (couche Curated).

Lit les données clean (factures enrichies API) depuis hdfs/clean/factures/api/<date>/,
calcule des agrégations (par pays, région, montants) et écrit dans hdfs/curated/analytics/<date>/.
Optionnel : upload des résultats vers le cluster HDFS via WebHDFS.

Déclenché après l'ingestion (schedule après multi_source_ingestion_factures ou manuel).
"""

from datetime import datetime, timedelta
import os
import json
from collections import defaultdict

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

HDFS_BASE = "/opt/airflow/hdfs"
CLEAN_BASE = os.path.join(HDFS_BASE, "clean", "factures", "api")
CURATED_BASE = os.path.join(HDFS_BASE, "curated", "analytics")
WEBHDFS_BASE = "http://hadoop-namenode:9870/webhdfs/v1"
HDFS_CLUSTER_BASE = "/datalake"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _upload_file_to_hdfs(local_path: str, hdfs_path: str, max_retries: int = 2) -> None:
    """Upload un fichier vers le cluster HDFS via WebHDFS (best-effort)."""
    for attempt in range(max_retries):
        try:
            parent_dir = os.path.dirname(hdfs_path)
            requests.put(
                f"{WEBHDFS_BASE}{parent_dir}",
                params={"op": "MKDIRS", "user.name": "hdfs"},
                timeout=30,
            )
            create_resp = requests.put(
                f"{WEBHDFS_BASE}{hdfs_path}",
                params={"op": "CREATE", "overwrite": "true", "user.name": "hdfs"},
                allow_redirects=False,
                timeout=30,
            )
            create_resp.raise_for_status()
            location = create_resp.headers.get("Location")
            if not location:
                raise RuntimeError("Pas de Location WebHDFS")
            with open(local_path, "rb") as f:
                requests.put(location, data=f, timeout=60).raise_for_status()
            return
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[WARN] Upload HDFS curated échoué: {e}")
            else:
                import time
                time.sleep(2 ** attempt)


def run_batch_analytics(**context):
    """
    Lit les factures enrichies (clean) du jour, calcule les agrégations,
    écrit les résultats en JSON dans curated/analytics/<date>/.
    """
    # logical_date (Airflow 2.2+) ou execution_date, ou ds (YYYY-MM-DD)
    today = context.get("logical_date") or context.get("execution_date") or context.get("ds")
    if hasattr(today, "strftime"):
        date_str = today.strftime("%Y-%m-%d")
    elif isinstance(today, str):
        date_str = today
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    clean_dir = os.path.join(CLEAN_BASE, date_str)
    raw_path = os.path.join(clean_dir, f"factures_api_enriched_{date_str}.json")

    if not os.path.exists(raw_path):
        return {
            "status": "no_input",
            "date": date_str,
            "message": f"Fichier clean absent: {raw_path}",
        }

    with open(raw_path, "r", encoding="utf-8") as f:
        invoices = json.load(f)

    # Agrégations
    by_country = defaultdict(lambda: {"count": 0, "montant_ttc_sum": 0.0, "montant_ht_sum": 0.0})
    by_region = defaultdict(lambda: {"count": 0, "montant_ttc_sum": 0.0})
    by_payment = defaultdict(lambda: {"count": 0, "montant_ttc_sum": 0.0})
    total_count = 0
    total_ttc = 0.0
    total_ht = 0.0

    for inv in invoices:
        pays = inv.get("pays") or "UNKNOWN"
        region = inv.get("country_region") or "UNKNOWN"
        mode = inv.get("mode_paiement") or "UNKNOWN"
        ht = float(inv.get("montant_ht") or 0)
        ttc = float(inv.get("montant_ttc") or 0)

        by_country[pays]["count"] += 1
        by_country[pays]["montant_ttc_sum"] += ttc
        by_country[pays]["montant_ht_sum"] += ht

        by_region[region]["count"] += 1
        by_region[region]["montant_ttc_sum"] += ttc

        by_payment[mode]["count"] += 1
        by_payment[mode]["montant_ttc_sum"] += ttc

        total_count += 1
        total_ttc += ttc
        total_ht += ht

    summary = {
        "date": date_str,
        "total_factures": total_count,
        "montant_ttc_total": round(total_ttc, 2),
        "montant_ht_total": round(total_ht, 2),
        "by_country": {k: {**v, "montant_ttc_sum": round(v["montant_ttc_sum"], 2), "montant_ht_sum": round(v["montant_ht_sum"], 2)} for k, v in by_country.items()},
        "by_region": {k: {**v, "montant_ttc_sum": round(v["montant_ttc_sum"], 2)} for k, v in by_region.items()},
        "by_payment": {k: {**v, "montant_ttc_sum": round(v["montant_ttc_sum"], 2)} for k, v in by_payment.items()},
    }

    out_dir = os.path.join(CURATED_BASE, date_str)
    _ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"analytics_summary_{date_str}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Upload optionnel vers HDFS distribué
    hdfs_curated = f"{HDFS_CLUSTER_BASE}/curated/analytics/{date_str}/analytics_summary_{date_str}.json"
    try:
        _upload_file_to_hdfs(out_path, hdfs_curated)
        hdfs_status = "uploaded"
    except Exception:
        hdfs_status = "error"

    return {
        "status": "ok",
        "date": date_str,
        "output_path": out_path,
        "hdfs_path": hdfs_curated,
        "hdfs_status": hdfs_status,
        "total_factures": total_count,
        "montant_ttc_total": round(total_ttc, 2),
    }


default_args = {
    "owner": "data-engineer",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="batch_analytics_factures",
    default_args=default_args,
    description="Agrégations batch des factures (clean → curated) pour exposition analytique",
    schedule_interval=timedelta(hours=1),  # Toutes les heures ; en prod on peut déclencher après ingestion
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["factures", "batch", "analytics", "curated"],
) as dag:
    analytics_task = PythonOperator(
        task_id="run_batch_analytics",
        python_callable=run_batch_analytics,
    )

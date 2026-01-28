from __future__ import annotations
from datetime import datetime, timedelta
import requests
import pandas as pd
from sqlalchemy import create_engine

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

# URL de l'API à interroger (dans le réseau Docker, le hostname doit correspondre au service)
API_URL = "http://mock-api:8099/orders?limit=20"  

# -----------------------------
# Fonction d'extraction
# -----------------------------
def extract_to_csv(**context):
    """
    Extrait les données depuis l'API et les sauvegarde au format CSV.
    Renvoie le chemin du fichier CSV pour les tâches suivantes.
    """
    # Requête HTTP GET vers l'API avec timeout de 10s
    r = requests.get(API_URL, timeout=10)
    
    # Lève une exception si le code HTTP n'est pas 2xx
    r.raise_for_status()
    
    # Récupère les lignes JSON dans la clé "rows"
    rows = r.json()["rows"]
    
    # Convertit en DataFrame pandas
    df = pd.DataFrame(rows)
    
    # Chemin de sortie CSV
    out_path = "/opt/airflow/data/extract_orders.csv"
    
    # Sauvegarde le CSV sans index
    df.to_csv(out_path, index=False)
    
    # Retourne le chemin pour XCom
    return out_path

# -----------------------------
# Fonction Data Quality
# -----------------------------
def data_quality(**context):
    """
    Vérifie la qualité des données extraites et logue les résultats.
    Retourne le nombre de lignes pour la décision de branchement.
    """
    ti = context["ti"]
    
    # Récupère le chemin du CSV depuis la task "extract"
    path = ti.xcom_pull(task_ids="extract", key="return_value")
    
    # Lit le CSV en DataFrame
    df = pd.read_csv(path)
    
    # Effectue plusieurs vérifications de qualité
    checks = {
        "total_rows": len(df),
        "has_null_values": df.isnull().any().any(),
        "duplicate_rows": df.duplicated().sum(),
        "empty_dataframe": df.empty
    }
    
    # Log des résultats
    print(f"Data Quality Checks:")
    for check, result in checks.items():
        print(f"  {check}: {result}")
    
    # Retourne le nombre de lignes pour la décision dans BranchPythonOperator
    return len(df)

# -----------------------------
# Fonction de branchement
# -----------------------------
def branch_on_row_count(**context):
    """
    Décide quelle branche suivre selon le nombre de lignes extraites.
    Si aucune donnée, on skip le chargement. Sinon, on continue vers Parquet et Postgres.
    """
    ti = context["ti"]
    
    # Récupère le nombre de lignes depuis la task "data_quality"
    row_count = ti.xcom_pull(task_ids="data_quality", key="return_value")
    
    if row_count == 0:
        print(f"⚠️  Aucune donnée trouvée ({row_count} lignes). Skip du chargement.")
        return "skip_load"  # Nom de la task à exécuter
    else:
        print(f"✅ {row_count} lignes trouvées. Chargement en Postgres.")
        return "export_parquet"

# -----------------------------
# Fonction Export Parquet
# -----------------------------
def export_parquet(**context):
    """
    Convertit le CSV en fichier Parquet.
    Essaie pyarrow en priorité, sinon fastparquet.
    """
    ti = context["ti"]
    path = ti.xcom_pull(task_ids="extract", key="return_value")
    df = pd.read_csv(path)
    
    parquet_path = "/opt/airflow/data/extract_orders.parquet"
    
    try:
        # Premier choix : moteur pyarrow
        df.to_parquet(parquet_path, index=False, engine="pyarrow")
        print(f"✅ Données exportées en Parquet (pyarrow): {parquet_path}")
    except ImportError:
        try:
            # Fallback : moteur fastparquet
            df.to_parquet(parquet_path, index=False, engine="fastparquet")
            print(f"✅ Données exportées en Parquet (fastparquet): {parquet_path}")
        except ImportError:
            # Si aucun moteur disponible, lever une erreur
            raise ImportError(
                "Aucun moteur Parquet disponible. Installez pyarrow ou fastparquet: pip install pyarrow"
            )
    
    # Retourne le chemin du fichier Parquet
    return parquet_path

# -----------------------------
# Fonction Load Postgres
# -----------------------------
def load_to_postgres(**context):
    """
    Charge les données dans PostgreSQL.
    Utilise une connexion SQLAlchemy explicite avec les identifiants corrects.
    """
    ti = context["ti"]
    path = ti.xcom_pull(task_ids="extract", key="return_value")
    df = pd.read_csv(path)
    
    # Connexion directe avec les identifiants du docker-compose
    # Format: postgresql+psycopg2://user:password@host:port/database
    connection_string = "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"
    engine = create_engine(connection_string)
    
    # Chargement dans la table "orders_staging", remplace si existante
    df.to_sql("orders_staging", engine, if_exists="replace", index=False)
    
    rows_loaded = int(df.shape[0])
    print(f"✅ {rows_loaded} lignes chargées dans PostgreSQL")
    return rows_loaded

# -----------------------------
# Définition du DAG
# -----------------------------
with DAG(
    dag_id="d3_etl_api_to_postgres",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # DAG déclenché manuellement
    catchup=False,  # Pas de rattrapage
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},  # Retry si échec
    tags=["m2", "day3"],
) as dag:
    
    # --- Task 1: Extraction ---
    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_to_csv
    )
    
    # --- Task 2: Data Quality ---
    data_quality_task = PythonOperator(
        task_id="data_quality",
        python_callable=data_quality
    )
    
    # --- Task 3: Branch conditionnel ---
    branch_task = BranchPythonOperator(
        task_id="branch_on_row_count",
        python_callable=branch_on_row_count
    )
    
    # --- Task 4: Export Parquet ---
    export_parquet_task = PythonOperator(
        task_id="export_parquet",
        python_callable=export_parquet
    )
    
    # --- Task 5: Chargement PostgreSQL ---
    load = PythonOperator(
        task_id="load",
        python_callable=load_to_postgres
    )
    
    # --- Task 6: Skip load (0 lignes) ---
    skip_load_task = EmptyOperator(
        task_id="skip_load"
    )
    
    # -----------------------------
    # Définition du flux (DAG)
    # -----------------------------
    extract >> data_quality_task >> branch_task
    branch_task >> export_parquet_task >> load  # Si données présentes
    branch_task >> skip_load_task  # Si 0 lignes

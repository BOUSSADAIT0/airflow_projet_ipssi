from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def extract(**context):
    payload = {"source": "mock", "rows": 3}
    return payload

def transform(ti):
    payload = ti.xcom_pull(task_ids="extract")
    payload["rows"] *= 10
    return payload

def load(ti):
    payload = ti.xcom_pull(task_ids="transform")
    print("Loading:", payload)

with DAG(
    dag_id="d2_xcom_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["m2", "day2"],
) as dag:
    t1 = PythonOperator(task_id="extract", python_callable=extract)
    t2 = PythonOperator(task_id="transform", python_callable=transform)
    t3 = PythonOperator(task_id="load", python_callable=load)
    t1 >> t2 >> t3

from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

def notify_sla_miss(dag, task_list, blocking_task_list, slas, blocking_tis, *args, **kwargs):
    print("SLA MISSED!")
    print("Tasks:", task_list)
    print("Blocking:", blocking_task_list)

with DAG(
    dag_id="d4_sla_and_retries",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    sla_miss_callback=notify_sla_miss,
    tags=["m2", "day4"],
) as dag:
    fast = BashOperator(task_id="fast_task", bash_command="sleep 1", sla=timedelta(seconds=5))
    slow = BashOperator(
        task_id="slow_task",
        bash_command="sleep 10",
        sla=timedelta(seconds=3),
        retries=1,
        retry_delay=timedelta(seconds=5),
    )
    fast >> slow

"""
DAG Airflow pour le traitement automatique de factures.
Orchestre l'extraction, validation et export des factures.

Chaque run (toutes les heures) :
  1. wait_for_invoice_file : sensor qui poke toutes les 60 s le dossier configuré (uploads/ + sous-dossiers).
  2. Dès qu'au moins un PDF/image est trouvé → check_invoice_files → process_all_invoices → validate → report.
  3. Timeout 55 min si aucun fichier : le run échoue, le prochain run réessaiera.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.python import PythonSensor

# Plus de check_interval / skip_run : chaque run vérifie directement le dossier uploads.

# Racine du projet : dans Docker = /opt/airflow/project, en local = parent de dags/
_PROJECT_ROOT = (
    '/opt/airflow/project'
    if os.path.exists('/opt/airflow/project')
    else os.path.join(os.path.dirname(__file__), '..')
)
INVOICE_DATA_FOLDER = os.path.join(_PROJECT_ROOT, 'data')

# Extensions considérées comme factures (PDF, images)
INVOICE_EXTENSIONS = ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']


def _get_upload_folder():
    """Dossier des factures : config utilisateur ou défaut (uploads)."""
    try:
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from user_config import resolve_source_folder
        return resolve_source_folder(_PROJECT_ROOT)
    except Exception:
        return os.path.join(_PROJECT_ROOT, 'uploads')


def _get_excel_path():
    """Fichier Excel de sortie : config utilisateur ou défaut."""
    try:
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from user_config import resolve_excel_path
        return resolve_excel_path(_PROJECT_ROOT)
    except Exception:
        return os.path.join(_PROJECT_ROOT, 'data', 'factures.xlsx')


def wait_for_any_invoice_file():
    """
    Callable pour le PythonSensor : retourne True dès qu'au moins un fichier
    facture (PDF ou image) est présent dans le dossier configuré (ou ses sous-dossiers).
    """
    upload_folder = Path(_get_upload_folder())
    upload_folder.mkdir(parents=True, exist_ok=True)
    print(f"[DAG] Vérification du dossier: {upload_folder} (existe={upload_folder.exists()})")
    for ext in INVOICE_EXTENSIONS:
        found = list(upload_folder.glob(ext)) or list(upload_folder.glob('**/' + ext))
        if found:
            print(f"[DAG] Fichier(s) trouvé(s): {[str(f) for f in found[:5]]}{'...' if len(found) > 5 else ''}")
            return True
    print(f"[DAG] Aucun fichier facture dans {upload_folder}")
    return False


def check_invoice_files(**context):
    """Vérifie s'il y a des fichiers factures à traiter (dossier configuré + sous-dossiers)."""
    upload_folder = Path(_get_upload_folder())
    upload_folder.mkdir(parents=True, exist_ok=True)
    print(f"[DAG] Dossier source: {upload_folder}")

    invoice_files = []
    for ext in INVOICE_EXTENSIONS:
        invoice_files.extend(list(upload_folder.glob(ext)))
        invoice_files.extend(list(upload_folder.glob('**/' + ext)))
    invoice_files = list(dict.fromkeys(invoice_files))

    if not invoice_files:
        print("[DAG] Aucun fichier facture à traiter")
        return "no_files"

    context['ti'].xcom_push(key='invoice_files', value=[str(f) for f in invoice_files])
    print(f"✅ {len(invoice_files)} fichier(s) facture(s) trouvé(s)")
    return "process_all_invoices"


def process_all_invoices(**context):
    """Traite toutes les factures trouvées (méthode auto = OpenAI si clé, sinon semantic)."""
    ti = context['ti']
    invoice_files = ti.xcom_pull(task_ids='check_invoice_files', key='invoice_files')
    method = context.get('params', {}).get('method', 'auto')

    if not invoice_files:
        print("Aucun fichier à traiter")
        return []

    results = []
    try:
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from invoice_processor import InvoiceProcessor

        processor = InvoiceProcessor()
        excel_path = _get_excel_path()

        for filepath in invoice_files:
            print(f"📄 Traitement de: {os.path.basename(filepath)}")
            result = processor.process_invoice(filepath, method)

            if result.get('success'):
                excel_result = processor.export_to_excel(result.get('data', {}), excel_path=excel_path)
                results.append({
                    'filepath': filepath,
                    'success': True,
                    'data': result.get('data', {}),
                    'excel_exported': excel_result.get('success', False)
                })
                print(f"✅ {os.path.basename(filepath)} traité avec succès")
            else:
                results.append({
                    'filepath': filepath,
                    'success': False,
                    'error': result.get('error', 'Erreur inconnue')
                })
                print(f"❌ {os.path.basename(filepath)}: {result.get('error')}")

        # Enregistrer le dernier run réussi pour l'intervalle
        try:
            from user_config import write_last_dag_run
            write_last_dag_run()
        except Exception:
            pass

        return results
    except Exception as e:
        print(f"Erreur process_all_invoices: {e}")
        raise


def validate_data(**context):
    """Valide les données extraites (placeholder : on pourrait vérifier champs obligatoires)."""
    ti = context['ti']
    results = ti.xcom_pull(task_ids='process_all_invoices')
    if not results:
        return
    success_count = sum(1 for r in results if r.get('success'))
    print(f"Validation : {success_count}/{len(results)} facture(s) traitées avec succès.")


def generate_report_task(**context):
    """Génère un résumé (logs)."""
    ti = context['ti']
    results = ti.xcom_pull(task_ids='process_all_invoices') or []
    print(f"Rapport : {len(results)} facture(s) traitées.")
    for r in results:
        status = "OK" if r.get('success') else r.get('error', '?')
        print(f"  - {os.path.basename(r.get('filepath', ''))}: {status}")


# DAG
with DAG(
    dag_id='projet_facture',
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': timedelta(minutes=2),
    },
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['factures', 'invoice'],
) as dag:

    wait_for_invoice = PythonSensor(
        task_id='wait_for_invoice_file',
        python_callable=wait_for_any_invoice_file,
        poke_interval=60,
        timeout=55 * 60,
        mode='poke',
    )
    check_files = BranchPythonOperator(
        task_id='check_invoice_files',
        python_callable=check_invoice_files
    )
    no_files = EmptyOperator(task_id='no_files')
    process_invoices = PythonOperator(
        task_id='process_all_invoices',
        python_callable=process_all_invoices
    )
    validate_data_task = PythonOperator(
        task_id='validate_data',
        python_callable=validate_data
    )
    generate_report_task_op = PythonOperator(
        task_id='generate_report_task',
        python_callable=generate_report_task
    )

    wait_for_invoice >> check_files >> [no_files, process_invoices]
    process_invoices >> validate_data_task >> generate_report_task_op

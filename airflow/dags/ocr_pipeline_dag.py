"""
DAG Airflow - Pipeline OCR Intelligent (traitement de fichiers uniquement)

Flux visible :
  1. Attendre qu'au moins un fichier soit déposé (PythonSensor)
  2. Obtenir un token API
  3. Lister les fichiers en attente
  4. Traiter chaque fichier (une tâche par fichier)

Déclenchement : dès qu'un fichier est présent dans le dossier inbox (upload via l'app
ou dépôt manuel), le sensor le détecte et le pipeline s'exécute.

Variables Airflow (Admin > Variables) :
- ocr_api_url, ocr_inbox_path, ocr_username, ocr_password
"""

from datetime import datetime, timedelta
import os
import logging
import requests
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.python import PythonSensor
from airflow.models import Variable
from airflow.decorators import task

logger = logging.getLogger(__name__)

OCR_API_URL = Variable.get("ocr_api_url", default_var="http://backend:8000")
OCR_INBOX_PATH = Variable.get("ocr_inbox_path", default_var="/opt/airflow/inbox")
OCR_USERNAME = Variable.get("ocr_username", default_var="aitdjoudi@gmail.com")
OCR_PASSWORD = Variable.get("ocr_password", default_var="boussad")

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


# --- Fonctions réutilisables ---

def _get_auth_token() -> str:
    url = f"{OCR_API_URL.rstrip('/')}/api/auth/login"
    resp = requests.post(
        url,
        data={"username": OCR_USERNAME, "password": OCR_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise ValueError("Pas de token dans la réponse login")
    return token


def _list_pending_files() -> list:
    """Liste les fichiers à traiter (inbox + sous-dossiers), en excluant uploads/processed/."""
    inbox = Path(OCR_INBOX_PATH)
    if not inbox.exists():
        return []
    files = []
    for f in inbox.rglob("*"):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS and "processed" not in f.parts:
            files.append(str(f))
    return sorted(files)


def _process_one_file(file_path: str, token: str) -> dict:
    url = f"{OCR_API_URL.rstrip('/')}/api/ocr/extract"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
        data = {"language": "fra+eng"}
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, files=files, data=data, headers=headers, timeout=120)
    resp.raise_for_status()
    out = resp.json()
    # Déplacer le fichier traité vers processed/ pour ne pas le retraiter au prochain run (fichier fermé ici)
    p = Path(file_path)
    processed_dir = Path(OCR_INBOX_PATH) / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / p.name
    if p.exists() and str(dest) != str(p.resolve()):
        try:
            import shutil
            shutil.move(str(p), str(dest))
            logger.info("Fichier déplacé vers processed/: %s", dest)
        except Exception as e:
            logger.warning("Impossible de déplacer vers processed/: %s", e)
    return out


# --- Sensor : attendre qu'au moins un fichier soit présent ---

def _poke_wait_for_file() -> bool:
    """Retourne True dès qu'au moins un fichier (PDF/image) est présent dans l'inbox."""
    inbox = Path(OCR_INBOX_PATH)
    if not inbox.exists():
        logger.warning("Dossier inbox inexistant : %s (vérifiez le volume monté)", OCR_INBOX_PATH)
        return False
    # Debug : lister le contenu du dossier (pour voir si le volume est le bon)
    try:
        all_items = list(inbox.rglob("*"))
        dirs = [p for p in all_items if p.is_dir()]
        any_files = [p for p in all_items if p.is_file()]
        logger.info("Inbox %s : %s sous-dossiers, %s fichiers (tous types). Fichiers éligibles : %s",
                    OCR_INBOX_PATH, len(dirs), len(any_files), _list_pending_files())
    except Exception as e:
        logger.warning("Impossible de lister l'inbox : %s", e)
    files = _list_pending_files()
    if files:
        logger.info("Fichier(s) détecté(s) dans %s : %s", OCR_INBOX_PATH, files)
        return True
    return False


# --- Tâches du DAG ---

@task
def get_token_task() -> str:
    """Tâche 1 : récupère le token JWT auprès de l'API OCR."""
    return _get_auth_token()


@task
def list_files_task() -> list:
    """Tâche 2 : liste les chemins des fichiers à traiter."""
    files = _list_pending_files()
    logger.info("Fichiers à traiter : %s", files)
    return files


@task
def process_file_task(path: str) -> dict:
    """Tâche 3 : envoie un fichier à l'API OCR (une tâche par fichier)."""
    from airflow.operators.python import get_current_context
    ti = get_current_context()["ti"]
    token = ti.xcom_pull(task_ids="get_token_task")
    if not token:
        raise ValueError("Token non disponible (get_token_task)")
    out = _process_one_file(path, token)
    logger.info("Traité %s -> process_id %s", path, out.get("process_id"))
    return {"file": path, "process_id": out.get("process_id"), "success": True}


@task
def resume_task(results: list = None) -> dict:
    """Tâche 4 : résumé du traitement (pour voir le flux)."""
    results = results or []
    total = len(results) if isinstance(results, list) else 0
    logger.info("Pipeline terminé : %s fichier(s) traité(s)", total)
    return {"total_processed": total, "results": results}


default_args = {
    "owner": "ocr-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="ocr_batch_pipeline",
    default_args=default_args,
    description="Traitement des fichiers par l'API OCR : sensor → token → liste → traitement par fichier",
    schedule_interval=timedelta(minutes=1),  # Toutes les 1 min : dès qu'un fichier est dans l'inbox, le sensor débloque et le pipeline se lance
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ocr", "batch", "documents", "file-processing"],
) as dag:

    start = EmptyOperator(task_id="start")

    wait_for_file = PythonSensor(
        task_id="wait_for_file",
        python_callable=_poke_wait_for_file,
        poke_interval=30,          # Vérifier toutes les 30 secondes
        timeout=60 * 60,          # Attendre au max 1 h qu'un fichier arrive
        mode="poke",
    )

    token = get_token_task()
    file_list = list_files_task()

    # Une tâche par fichier (mapping dynamique)
    processed = process_file_task.expand(path=file_list)

    # Résumé (consomme la liste des résultats pour afficher le flux)
    summary = resume_task(processed)

    end = EmptyOperator(task_id="end")

    # Flux : start → wait_for_file → [get_token, list_files] → process_file (×N) → resume → end
    start >> wait_for_file >> [token, file_list]
    [token, file_list] >> processed
    processed >> summary
    file_list >> summary  # résumé s'exécute même si 0 fichier (processed skipped)
    summary >> end

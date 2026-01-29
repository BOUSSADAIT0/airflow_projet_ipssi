"""
Configuration utilisateur : dossier des factures, fichier Excel de sortie, intervalle du DAG.
Partagée entre l'app web (Flask) et le DAG Airflow.
"""
import os
import json
from pathlib import Path

# Dossier data à la racine du projet (ou /opt/airflow/project/data en Docker)
def _config_dir():
    root = os.environ.get('PROJECT_ROOT', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'data')

CONFIG_PATH = os.path.join(_config_dir(), 'user_config.json')
LAST_RUN_PATH = os.path.join(_config_dir(), 'last_dag_run.txt')

DEFAULT_CONFIG = {
    'invoice_source_path': 'uploads',
    'invoice_output_excel': 'data/factures.xlsx',
    'dag_interval_hours': 1,
}

def load_user_config():
    """Charge la config utilisateur (dossier source, Excel sortie, intervalle DAG)."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)

def save_user_config(config):
    """Enregistre la config utilisateur."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return True

def resolve_source_folder(project_root):
    """Retourne le chemin absolu du dossier des factures (config ou défaut)."""
    cfg = load_user_config()
    path = cfg.get('invoice_source_path') or DEFAULT_CONFIG['invoice_source_path']
    if not os.path.isabs(path):
        path = os.path.join(project_root, path)
    return os.path.normpath(path)

def resolve_excel_path(project_root):
    """Retourne le chemin absolu du fichier Excel de sortie (config ou défaut)."""
    cfg = load_user_config()
    path = cfg.get('invoice_output_excel') or DEFAULT_CONFIG['invoice_output_excel']
    if not os.path.isabs(path):
        path = os.path.join(project_root, path)
    return os.path.normpath(path)

def get_dag_interval_hours():
    """Retourne l'intervalle en heures entre deux runs du DAG (config ou 1)."""
    cfg = load_user_config()
    return float(cfg.get('dag_interval_hours') or 1)

def read_last_dag_run():
    """Lit le timestamp du dernier run réussi du DAG (secondes depuis epoch)."""
    try:
        if os.path.exists(LAST_RUN_PATH):
            with open(LAST_RUN_PATH, 'r', encoding='utf-8') as f:
                return float(f.read().strip())
    except Exception:
        pass
    return 0.0

def write_last_dag_run():
    """Enregistre le timestamp actuel comme dernier run réussi."""
    os.makedirs(os.path.dirname(LAST_RUN_PATH), exist_ok=True)
    import time
    with open(LAST_RUN_PATH, 'w', encoding='utf-8') as f:
        f.write(str(time.time()))
    return True

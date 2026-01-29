"""
Callable pour Airflow : hostname utilisé dans l'URL des logs (serveur sur le scheduler, port 8793).
Retourne 'localhost' pour que le navigateur puisse charger les logs via http://localhost:8793/...
"""


def get_hostname():
    return "localhost"

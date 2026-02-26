"""
API Analytics : exposition des agrégations factures (couche curated).
Lit les fichiers générés par le DAG batch_analytics_factures depuis CURATED_PATH.
"""
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Monté en Docker : ./hdfs/curated -> /app/data/curated → analytics/<date>/analytics_summary_<date>.json
CURATED_PATH = os.environ.get("CURATED_PATH", "/app/data/curated")
if not os.path.isabs(CURATED_PATH):
    # En local : projet/backend/app/api -> parents[3] = racine projet
    _root = Path(__file__).resolve().parents[3]
    CURATED_PATH = str(_root / "hdfs" / "curated")
ANALYTICS_BASE = Path(CURATED_PATH) / "analytics"


def _list_curated_dates() -> list[str]:
    if not ANALYTICS_BASE.exists():
        return []
    return sorted([d.name for d in ANALYTICS_BASE.iterdir() if d.is_dir()], reverse=True)


def _load_summary(date: str) -> dict[str, Any] | None:
    path = ANALYTICS_BASE / date / f"analytics_summary_{date}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        import json
        return json.load(f)


def _get_demo_summary():
    """Données de démonstration quand le Data Lake n'a pas encore de curated."""
    from datetime import datetime
    d = datetime.now().strftime("%Y-%m-%d")
    return {
        "date": d,
        "total_factures": 1250,
        "montant_ttc_total": 187540.50,
        "montant_ht_total": 156283.75,
        "by_country": {
            "FR": {"count": 420, "montant_ttc_sum": 62800.20, "montant_ht_sum": 52333.50},
            "DE": {"count": 310, "montant_ttc_sum": 46520.10, "montant_ht_sum": 38766.75},
            "ES": {"count": 280, "montant_ttc_sum": 42100.80, "montant_ht_sum": 35084.00},
            "IT": {"count": 240, "montant_ttc_sum": 36119.40, "montant_ht_sum": 30099.50},
        },
        "by_region": {
            "Europe": {"count": 1250, "montant_ttc_sum": 187540.50},
            "Western Europe": {"count": 850, "montant_ttc_sum": 127540.20},
        },
        "by_payment": {
            "CB": {"count": 520, "montant_ttc_sum": 78020.00},
            "VIREMENT": {"count": 380, "montant_ttc_sum": 57100.50},
            "PAYPAL": {"count": 250, "montant_ttc_sum": 37500.25},
            "CHEQUE": {"count": 100, "montant_ttc_sum": 14920.00},
        },
    }


@router.get("/summary")
async def get_summary(date: str | None = None):
    """
    Résumé global : total factures, montants TTC/HT.
    Si date fournie, retourne le résumé du jour ; sinon le dernier disponible.
    Si aucune donnée curated : retourne des données de démo pour afficher les graphiques.
    """
    dates = _list_curated_dates()
    if not dates:
        demo = _get_demo_summary()
        demo["_demo"] = True
        return demo
    target = date if date and date in dates else dates[0]
    data = _load_summary(target)
    if not data:
        demo = _get_demo_summary()
        demo["date"] = target
        demo["_demo"] = True
        return demo
    return {
        "date": data.get("date"),
        "total_factures": data.get("total_factures", 0),
        "montant_ttc_total": data.get("montant_ttc_total", 0),
        "montant_ht_total": data.get("montant_ht_total", 0),
        "by_country": data.get("by_country", {}),
        "by_region": data.get("by_region", {}),
        "by_payment": data.get("by_payment", {}),
    }


@router.get("/by_region")
async def get_by_region(date: str | None = None):
    """Agrégats par région (country_region)."""
    dates = _list_curated_dates()
    if not dates:
        return {"message": "Aucune donnée curated", "by_region": {}}
    target = date if date and date in dates else dates[0]
    data = _load_summary(target)
    if not data:
        raise HTTPException(status_code=404, detail=f"Résumé absent pour {target}")
    return {"date": target, "by_region": data.get("by_region", {})}


@router.get("/by_country")
async def get_by_country(date: str | None = None):
    """Agrégats par pays."""
    dates = _list_curated_dates()
    if not dates:
        return {"message": "Aucune donnée curated", "by_country": {}}
    target = date if date and date in dates else dates[0]
    data = _load_summary(target)
    if not data:
        raise HTTPException(status_code=404, detail=f"Résumé absent pour {target}")
    return {"date": target, "by_country": data.get("by_country", {})}


@router.get("/dates")
async def list_dates():
    """Liste des dates pour lesquelles des agrégations curated existent. Au moins la date du jour en démo."""
    dates = _list_curated_dates()
    if not dates:
        from datetime import datetime
        dates = [datetime.now().strftime("%Y-%m-%d")]
    return {"dates": dates}

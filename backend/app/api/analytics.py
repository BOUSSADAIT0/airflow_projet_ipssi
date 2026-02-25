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


@router.get("/summary")
async def get_summary(date: str | None = None):
    """
    Résumé global : total factures, montants TTC/HT.
    Si date fournie, retourne le résumé du jour ; sinon le dernier disponible.
    """
    dates = _list_curated_dates()
    if not dates:
        return {"message": "Aucune donnée curated disponible", "dates": []}
    target = date if date and date in dates else dates[0]
    data = _load_summary(target)
    if not data:
        raise HTTPException(status_code=404, detail=f"Résumé absent pour {target}")
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
    """Liste des dates pour lesquelles des agrégations curated existent."""
    return {"dates": _list_curated_dates()}

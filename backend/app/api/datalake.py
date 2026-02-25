"""
API Data Lake / HDFS : structure du stockage et dépôt de fichiers vers le Data Lake.
Les fichiers déposés sont enregistrés dans la zone raw (équivalent HDFS) et peuvent
être synchronisés vers le cluster HDFS via le script sync_hdfs_to_datalake.sh.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/datalake", tags=["datalake"])

# Base du Data Lake (monté en Docker : ./hdfs -> /app/data/hdfs)
HDFS_BASE = os.environ.get("HDFS_BASE", "/app/data/hdfs")
if not os.path.isabs(HDFS_BASE):
    _root = Path(__file__).resolve().parents[3]
    HDFS_BASE = str(_root / "hdfs")

ZONES = ("raw", "clean", "curated")
ALLOWED_UPLOAD_EXT = (".csv", ".json")


def _safe_list_dir(path: Path, max_depth: int = 4) -> list[dict[str, Any]]:
    """Liste récursive limitée pour construire l'arbre."""
    if max_depth <= 0:
        return []
    items = []
    try:
        for p in sorted(path.iterdir()):
            rel = p.relative_to(path)
            node = {"name": rel.name, "path": str(rel)}
            if p.is_dir():
                children = _safe_list_dir(p, max_depth - 1)
                node["type"] = "dir"
                node["children"] = children
                node["count"] = len(children)
            else:
                node["type"] = "file"
                try:
                    node["size"] = p.stat().st_size
                except OSError:
                    node["size"] = 0
            items.append(node)
    except (OSError, PermissionError):
        pass
    return items


@router.get("/structure")
async def get_structure():
    """
    Retourne la structure du Data Lake (zones raw, clean, curated).
    Les données sont stockées localement et synchronisables vers le cluster HDFS.
    """
    base = Path(HDFS_BASE)
    if not base.exists():
        return {
            "message": "Data Lake non monté (vérifier le volume ./hdfs)",
            "zones": {},
            "hdfs_ui_url": "/api/datalake/hdfs-ui-url",
        }
    zones = {}
    for zone in ZONES:
        zone_path = base / zone
        if zone_path.is_dir():
            zones[zone] = {
                "path": zone,
                "description": {
                    "raw": "Données brutes (fichiers, DB, API)",
                    "clean": "Données enrichies (nettoyées)",
                    "curated": "Agrégations analytiques",
                }.get(zone, ""),
                "tree": _safe_list_dir(zone_path),
            }
        else:
            zones[zone] = {"path": zone, "description": "", "tree": []}
    return {
        "zones": zones,
        "base_path": str(base),
        "hdfs_ui_url": "http://localhost:9870",
    }


@router.get("/hdfs-ui-url")
async def get_hdfs_ui_url():
    """URL de l'interface Web HDFS (NameNode) pour parcourir le cluster."""
    return {"url": "http://localhost:9870", "label": "Ouvrir l'interface HDFS (NameNode)"}


@router.post("/upload")
async def upload_to_datalake(file: UploadFile = File(...)):
    """
    Dépose un fichier dans la zone raw du Data Lake (raw/factures/files/<date>/).
    Formats acceptés : CSV, JSON.
    Le fichier sera visible dans le Data Lake et pourra être synchronisé vers HDFS.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Format non autorisé. Utilisez {', '.join(ALLOWED_UPLOAD_EXT)}",
        )
    base = Path(HDFS_BASE)
    if not base.exists():
        raise HTTPException(status_code=503, detail="Data Lake non disponible (volume non monté)")
    date_str = datetime.now().strftime("%Y-%m-%d")
    target_dir = base / "raw" / "factures" / "files" / date_str
    target_dir.mkdir(parents=True, exist_ok=True)
    # Nom unique pour éviter écrasement
    safe_name = file.filename
    target_path = target_dir / safe_name
    try:
        content = await file.read()
        target_path.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Erreur écriture: {e}")
    return {
        "message": "Fichier déposé dans le Data Lake (zone raw)",
        "path": f"raw/factures/files/{date_str}/{safe_name}",
        "full_path": str(target_path),
        "size": len(content),
        "date_zone": date_str,
    }

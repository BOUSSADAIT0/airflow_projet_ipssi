# Imports retirés pour éviter circular import au chargement de app.api.analytics / app.api.datalake.
# Les modules qui en ont besoin font : from app.api.ocr import router as ocr_router
__all__ = []
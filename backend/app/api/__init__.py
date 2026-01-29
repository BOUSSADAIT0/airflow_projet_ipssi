from app.api.ocr import router as ocr_router
from app.api.results import router as results_router
from app.api.auth import router as auth_router

__all__ = ["ocr_router", "results_router", "auth_router"]
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class OCRRequest(BaseModel):
    file_content: str  # Base64
    filename: str
    language: str = "fra+eng"
    export_format: str = "json"

class OCRResponse(BaseModel):
    success: bool
    process_id: str
    filename: str
    document_type: str
    confidence: float
    extracted_data: Dict[str, Any]
    processing_time: float
    preview_url: Optional[str] = None
    download_urls: Dict[str, str] = {}

class BatchOCRRequest(BaseModel):
    files: List[OCRRequest]
    user_id: Optional[int] = None

class BatchOCRResponse(BaseModel):
    success: bool
    total_files: int
    successful_files: int
    failed_files: int
    results: List[OCRResponse]
    batch_id: str
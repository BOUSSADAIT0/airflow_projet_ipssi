from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class ExtractionResultBase(BaseModel):
    process_id: str
    confidence_score: float

class ExtractionResultCreate(BaseModel):
    document_id: int
    extracted_data: Dict[str, Any]
    raw_text: str
    zones: List[Dict[str, Any]]
    preview_path: Optional[str] = None
    confidence_score: float

class ExtractionResult(ExtractionResultBase):
    id: int
    document_id: int
    user_id: int
    extraction_date: datetime
    processing_time: float
    json_path: Optional[str] = None
    csv_path: Optional[str] = None
    excel_path: Optional[str] = None
    preview_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class ExportRequest(BaseModel):
    process_id: str
    format: str

class ExportResponse(BaseModel):
    success: bool
    format: str
    filename: str
    download_url: str
    file_size: int
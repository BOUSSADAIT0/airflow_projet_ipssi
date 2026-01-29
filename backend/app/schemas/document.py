from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    filename: str
    document_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    document_type: Optional[str] = None
    error_message: Optional[str] = None

class Document(DocumentBase):
    id: int
    user_id: int
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_date: datetime
    processed_date: Optional[datetime] = None
    status: str
    page_count: int = 1
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
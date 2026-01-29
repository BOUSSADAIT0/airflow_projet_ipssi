from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base

class ExtractionResult(Base):
    __tablename__ = "extraction_results"
    
    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(String, unique=True, index=True)
    
    extracted_data = Column(JSON)
    raw_text = Column(Text)
    confidence_score = Column(Float)
    
    zones = Column(JSON)
    preview_path = Column(String)
    
    extraction_date = Column(DateTime, default=func.now())
    processing_time = Column(Float)
    
    json_path = Column(String)
    csv_path = Column(String)
    excel_path = Column(String)
    
    document_id = Column(Integer, ForeignKey("documents.id"))
    document = relationship("Document", back_populates="extraction_results")
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="extraction_results")
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    file_type = Column(String)
    mime_type = Column(String)
    
    upload_date = Column(DateTime, default=func.now())
    processed_date = Column(DateTime)
    document_type = Column(String)
    page_count = Column(Integer, default=1)
    
    status = Column(String, default="pending")
    error_message = Column(Text)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    
    extraction_results = relationship("ExtractionResult", back_populates="document")
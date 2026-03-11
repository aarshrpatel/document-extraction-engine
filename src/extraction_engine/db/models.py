import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from extraction_engine.db.session import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    doc_type = Column(String(50), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    file_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    extraction_results = relationship("ExtractionResult", back_populates="document")


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    extracted_data = Column(JSONB, nullable=False)
    raw_llm_response = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    model_version = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="extraction_results")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    doc_type = Column(String(50), nullable=False)
    total_documents = Column(Integer, nullable=False)
    avg_field_accuracy = Column(Float, nullable=True)
    avg_levenshtein_score = Column(Float, nullable=True)
    report_json = Column(JSONB, nullable=True)

    eval_results = relationship("EvalResult", back_populates="eval_run")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eval_run_id = Column(Integer, ForeignKey("eval_runs.id"), nullable=False)
    document_id = Column(String(200), nullable=False)
    field_name = Column(String(200), nullable=False)
    expected_value = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    levenshtein_distance = Column(Integer, nullable=True)
    similarity_score = Column(Float, nullable=True)

    eval_run = relationship("EvalRun", back_populates="eval_results")

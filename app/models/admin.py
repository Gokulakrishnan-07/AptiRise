from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
)
from sqlalchemy.orm import relationship
from app.database import Base


class PdfImport(Base):
    __tablename__ = "pdf_imports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="pending")  # pending, processing, reviewed, approved, rejected
    total_detected = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    target_collection_id = Column(Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)
    target_level_id = Column(Integer, ForeignKey("levels.id", ondelete="SET NULL"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("PdfImportQuestion", back_populates="pdf_import", cascade="all, delete-orphan")


class PdfImportQuestion(Base):
    __tablename__ = "pdf_import_questions"

    id = Column(Integer, primary_key=True, index=True)
    pdf_import_id = Column(Integer, ForeignKey("pdf_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    detected_answer = Column(String(5), nullable=False)  # A, B, C, D
    detected_explanation = Column(Text, nullable=True)
    detected_shortcut = Column(Text, nullable=True)
    detected_topic = Column(String(100), nullable=True)
    detected_difficulty = Column(String(30), default="Intermediate")
    ai_confidence = Column(Float, default=0.85)  # 0.0 - 1.0
    status = Column(String(30), default="pending")  # pending, approved, rejected, duplicate
    duplicate_question_id = Column(Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    is_duplicate = Column(Boolean, default=False)
    final_collection_id = Column(Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)
    final_level_id = Column(Integer, ForeignKey("levels.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pdf_import = relationship("PdfImport", back_populates="questions")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)  # question, collection, pdf_import, user, setting
    target_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

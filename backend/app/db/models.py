import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Assessee(Base):
    __tablename__ = "assessees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pan = Column(String(10), unique=True, index=True, nullable=False)
    legal_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=True)
    phone = Column(String(15), nullable=True)
    entity_type = Column(String(50), default="INDIVIDUAL")
    dpdp_consent_granted = Column(Boolean, default=True, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sessions = relationship("IntakeSession", back_populates="assessee", cascade="all, delete-orphan")
    reconciliations = relationship("ReconciliationRecord", back_populates="assessee", cascade="all, delete-orphan")

class IntakeSession(Base):
    __tablename__ = "intake_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessee_id = Column(UUID(as_uuid=True), ForeignKey("assessees.id"), nullable=True)
    session_token = Column(String(64), unique=True, index=True, nullable=False)
    channel = Column(String(20), default="VOICE_BROWSER")
    recommended_form = Column(String(20), nullable=True)
    applicable_regime = Column(String(20), default="115BAC")
    estimated_turnover = Column(Numeric(precision=14, scale=2), default=Decimal("0.00"))
    estimated_tax = Column(Numeric(precision=14, scale=2), default=Decimal("0.00"))
    is_completed = Column(Boolean, default=False)
    audit_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    assessee = relationship("Assessee", back_populates="sessions")
    messages = relationship("IntakeMessage", back_populates="session", cascade="all, delete-orphan")

class IntakeMessage(Base):
    __tablename__ = "intake_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("intake_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    audio_latency_ms = Column(Numeric(precision=8, scale=2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("IntakeSession", back_populates="messages")

class ReconciliationRecord(Base):
    __tablename__ = "reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessee_id = Column(UUID(as_uuid=True), ForeignKey("assessees.id"), nullable=True)
    return_type = Column(String(20), default="GSTR_36_4")
    total_pr_invoices = Column(Numeric(precision=8, scale=0), default=0)
    total_2b_invoices = Column(Numeric(precision=8, scale=0), default=0)
    matched_itc = Column(Numeric(precision=14, scale=2), default=Decimal("0.00"))
    ineligible_itc = Column(Numeric(precision=14, scale=2), default=Decimal("0.00"))
    missing_in_2b_itc = Column(Numeric(precision=14, scale=2), default=Decimal("0.00"))
    computation_hash = Column(String(64), nullable=False)
    status = Column(String(20), default="COMPLETED")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    assessee = relationship("Assessee", back_populates="reconciliations")

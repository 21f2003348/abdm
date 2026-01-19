from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database.connection import Base
import uuid
from datetime import datetime

class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    mobile = Column(String, unique=True, nullable=False)
    abha_id = Column(String, unique=True, nullable=True)
    aadhaar = Column(String, unique=True, nullable=True)

    visits = relationship("Visit", back_populates="patient")
    care_contexts = relationship("CareContext", back_populates="patient")
    health_records = relationship("HealthRecord", back_populates="patient")

class Visit(Base):
    __tablename__ = "visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    visit_type = Column(String, nullable=False)
    department = Column(String, nullable=False)
    doctor_id = Column(String, nullable=True)
    visit_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="Scheduled", nullable=False)

    patient = relationship("Patient", back_populates="visits")

class CareContext(Base):
    __tablename__ = "care_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    context_name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="care_contexts")


class HealthRecord(Base):
    """
    Store health records received from other hospitals via ABDM Gateway.
    Supports both local records and external records with encryption support.
    """
    __tablename__ = "health_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    
    # Record metadata
    record_type = Column(String, nullable=False)  # PRESCRIPTION, DIAGNOSTIC_REPORT, LAB_REPORT, etc.
    record_date = Column(DateTime, nullable=False)  # When the record was created
    
    # Data storage
    data_json = Column(JSON, nullable=False)  # Actual health record data (structured)
    data_text = Column(Text, nullable=True)  # Text representation if needed
    
    # Source tracking
    source_hospital = Column(String, nullable=True)  # Which hospital sent it (bridge_id)
    request_id = Column(String, nullable=True)  # Gateway request ID for tracking
    
    # Encryption tracking
    was_encrypted = Column(Boolean, default=False)  # Whether it arrived encrypted
    decryption_status = Column(String, default="NONE")  # NONE, PENDING, SUCCESS, FAILED
    
    # Delivery tracking
    delivery_attempt = Column(Integer, default=0)  # How many times delivery was attempted
    last_delivery_timestamp = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="health_records")
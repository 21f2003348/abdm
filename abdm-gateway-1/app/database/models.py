from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, nullable=False)
    client_secret = Column(String, nullable=False)


class Patient(Base):
    """
    Central patient registry in the gateway.
    Stores ABHA-linked patient information for cross-hospital coordination.
    """
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    abha_id = Column(String, unique=True, nullable=False, index=True)  # ABHA ID (unique identifier)
    abha_address = Column(String, nullable=True)  # ABHA address (e.g., user@abdm)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=True)
    gender = Column(String, nullable=True)  # Male, Female, Other
    date_of_birth = Column(DateTime, nullable=True)
    
    # Relationships
    linking_requests = relationship("LinkingRequest", back_populates="patient")
    care_contexts = relationship("LinkedCareContext", back_populates="patient")
    consent_requests = relationship("ConsentRequest", back_populates="patient")
    data_transfers = relationship("DataTransfer", back_populates="patient")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bridge(Base):
    __tablename__ = "bridges"

    id = Column(Integer, primary_key=True, index=True)
    bridge_id = Column(String, unique=True, nullable=False)
    entity_type = Column(String, nullable=False)  # e.g., "HIP", "HIU"
    name = Column(String, nullable=False)
    webhook_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BridgeService(Base):
    __tablename__ = "bridge_services"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, unique=True, nullable=False)
    bridge_id = Column(String, nullable=False)
    service_name = Column(String, nullable=False)
    service_type = Column(String, nullable=False)  # e.g., "LAB", "PHARMACY"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LinkingRequest(Base):
    __tablename__ = "linking_requests"

    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(String, unique=True, nullable=False)
    patient_abha_id = Column(String, ForeignKey("patients.abha_id"), nullable=False, index=True)
    hip_id = Column(String, nullable=False)
    mobile = Column(String, nullable=True)
    status = Column(String, default="INITIATED")  # INITIATED, LINKED, FAILED
    link_token = Column(String, nullable=True)
    
    # Relationship
    patient = relationship("Patient", back_populates="linking_requests")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LinkedCareContext(Base):
    __tablename__ = "linked_care_contexts"

    id = Column(Integer, primary_key=True, index=True)
    patient_abha_id = Column(String, ForeignKey("patients.abha_id"), nullable=False, index=True)
    care_context_id = Column(String, unique=True, nullable=False)
    reference_number = Column(String, nullable=False)
    hip_id = Column(String, nullable=False)
    
    # Relationship
    patient = relationship("Patient", back_populates="care_contexts")
    
    linked_at = Column(DateTime, default=datetime.utcnow)


class ConsentRequest(Base):
    __tablename__ = "consent_requests"

    id = Column(Integer, primary_key=True, index=True)
    consent_request_id = Column(String, unique=True, nullable=False)
    patient_abha_id = Column(String, ForeignKey("patients.abha_id"), nullable=False, index=True)
    hip_id = Column(String, nullable=False)
    purpose = Column(JSON, nullable=False)
    status = Column(String, default="INITIATED")  # INITIATED, APPROVED, REJECTED, EXPIRED
    
    # Relationship
    patient = relationship("Patient", back_populates="consent_requests")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataTransfer(Base):
    __tablename__ = "data_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(String, unique=True, nullable=False)
    consent_request_id = Column(String, nullable=False)
    patient_abha_id = Column(String, ForeignKey("patients.abha_id"), nullable=False, index=True)
    from_entity = Column(String, nullable=False)  # HIP
    to_entity = Column(String, nullable=False)  # HIU
    status = Column(String, default="REQUESTED")  # REQUESTED, FORWARDED, PROCESSING, READY, DELIVERED, FAILED
    data_count = Column(Integer, default=0)
    
    # Relationship
    patient = relationship("Patient", back_populates="data_transfers")
    
    # Encrypted temporary data storage
    encrypted_data = Column(String, nullable=True)  # Encrypted health data
    
    # Webhook retry mechanism
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    webhook_attempts = Column(Integer, default=0)
    last_webhook_error = Column(String, nullable=True)
    
    # TTL for temporary storage
    expires_at = Column(DateTime, nullable=True)  # Data expires after 24 hours
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
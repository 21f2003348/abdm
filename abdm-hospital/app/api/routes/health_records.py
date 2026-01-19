"""
Health Records API Routes for ABDM Hospital.
Provides endpoints to view, manage, and track health records.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import uuid

from app.database.connection import get_db
from app.database.models import HealthRecord, Patient
from app.services.health_data_service import (
    get_health_records_for_patient,
    get_external_health_records,
    get_health_record_summary
)

router = APIRouter(prefix="/api/health-records", tags=["health-records"])


# ============================================================================
# Schemas
# ============================================================================

class HealthRecordResponse(BaseModel):
    id: str
    type: str
    date: str
    sourceHospital: Optional[str]
    data: Dict[str, Any]
    receivedAt: str
    requestId: Optional[str] = None
    # Additional fields for frontend display
    patientId: Optional[str] = None
    patientName: Optional[str] = None
    title: Optional[str] = None  # Derived from record type or data

    class Config:
        from_attributes = True


class HealthRecordSummaryResponse(BaseModel):
    totalRecords: int
    byType: Dict[str, int]
    bySource: Dict[str, int]
    lastUpdated: str


class CreateHealthRecordRequest(BaseModel):
    recordType: str
    recordDate: str
    data: Dict[str, Any]
    dataText: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/")
async def list_all_patients_with_records(
    db: Session = Depends(get_db)
):
    """
    List all patients that have health records.
    
    Returns:
    - List of patients with record counts
    """
    # Get all patients
    patients = db.execute(select(Patient)).scalars().all()
    
    result = []
    for patient in patients:
        # Count records for this patient
        record_count = db.execute(
            select(HealthRecord).where(HealthRecord.patient_id == patient.id)
        ).scalars().all()
        
        if len(record_count) > 0:
            result.append({
                "patientId": str(patient.id),
                "name": patient.name,
                "mobile": patient.mobile,
                "abhaId": patient.abha_id,
                "recordCount": len(record_count)
            })
    
    return {
        "total": len(result),
        "patients": result
    }


@router.get("/{patient_id}", response_model=List[HealthRecordResponse])
async def list_health_records(
    patient_id: str,
    record_type: Optional[str] = Query(None, description="Filter by record type (e.g., PRESCRIPTION)"),
    source_hospital: Optional[str] = Query(None, description="Filter by source hospital"),
    db: Session = Depends(get_db)
):
    """
    List all health records for a patient.
    
    Query Parameters:
    - record_type: Optional filter by type (PRESCRIPTION, DIAGNOSTIC_REPORT, etc.)
    - source_hospital: Optional filter by source hospital bridge ID
    
    Returns:
    - List of health records with all details
    """
    records = await get_health_records_for_patient(
        db=db,
        patient_id=patient_id,
        record_type=record_type,
        source_hospital=source_hospital
    )
    
    if not records:
        # Check if patient exists
        try:
            patient_uuid = uuid.UUID(patient_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient ID format")
        
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient {patient_id} not found"
            )
        
        return []
    
    return records


@router.get("/{patient_id}/summary", response_model=HealthRecordSummaryResponse)
async def get_patient_health_summary(
    patient_id: str,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics of health records for a patient.
    
    Returns:
    - Total count
    - Count by record type
    - Count by source hospital
    - Last updated timestamp
    """
    # Check if patient exists
    try:
        patient_uuid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID format")
    
    patient = db.execute(
        select(Patient).where(Patient.id == patient_uuid)
    ).scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found"
        )
    
    summary = await get_health_record_summary(db=db, patient_id=patient_id)
    return summary


@router.get("/{patient_id}/external", response_model=List[HealthRecordResponse])
async def list_external_health_records(
    patient_id: str,
    db: Session = Depends(get_db)
):
    """
    List only health records received from other hospitals via ABDM Gateway.
    
    Returns:
    - List of external health records (those with source_hospital set)
    """
    # Check if patient exists
    try:
        patient_uuid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID format")
    
    patient = db.execute(
        select(Patient).where(Patient.id == patient_uuid)
    ).scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found"
        )
    
    records = await get_external_health_records(db=db, patient_id=patient_id)
    return records


@router.get("/{patient_id}/{record_id}", response_model=HealthRecordResponse)
async def get_health_record_details(
    patient_id: str,
    record_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific health record.
    
    Returns:
    - Complete health record with all fields
    """
    # Convert IDs to UUID
    try:
        patient_uuid = uuid.UUID(patient_id)
        record_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Query for the specific record
    record = db.execute(
        select(HealthRecord).where(
            and_(
                HealthRecord.id == record_uuid,
                HealthRecord.patient_id == patient_uuid
            )
        )
    ).scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Health record {record_id} not found for patient {patient_id}"
        )
    
    return {
        "id": str(record.id),
        "type": record.record_type,
        "date": record.record_date.isoformat(),
        "sourceHospital": record.source_hospital,
        "data": record.data_json,
        "receivedAt": record.created_at.isoformat(),
        "requestId": record.request_id
    }


@router.post("/{patient_id}", response_model=HealthRecordResponse)
async def create_health_record(
    patient_id: str,
    request: CreateHealthRecordRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new health record for a patient (internal use).
    
    This is used for locally generated health records,
    not for records received via ABDM Gateway.
    
    Body:
    - recordType: Type of record (PRESCRIPTION, DIAGNOSTIC_REPORT, etc.)
    - recordDate: ISO 8601 date string
    - data: JSON object with record details
    - dataText: Optional text representation
    
    Returns:
    - Created health record
    """
    # Check if patient exists
    try:
        patient_uuid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID format")
    
    patient = db.execute(
        select(Patient).where(Patient.id == patient_uuid)
    ).scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found"
        )
    
    # Create new health record
    new_record = HealthRecord(
        id=uuid.uuid4(),
        patient_id=patient_uuid,
        record_type=request.recordType,
        record_date=datetime.fromisoformat(request.recordDate),
        data_json=request.data,
        data_text=request.dataText,
        source_hospital=None,  # Local record
        request_id=None,
        was_encrypted=False,
        decryption_status="NONE",
        delivery_attempt=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    return {
        "id": str(new_record.id),
        "type": new_record.record_type,
        "date": new_record.record_date.isoformat(),
        "sourceHospital": new_record.source_hospital,
        "data": new_record.data_json,
        "receivedAt": new_record.created_at.isoformat(),
        "requestId": new_record.request_id
    }


@router.delete("/{patient_id}/{record_id}")
async def delete_health_record(
    patient_id: str,
    record_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific health record.
    
    WARNING: This permanently deletes the health record.
    Use with caution, especially for records received from other hospitals.
    
    Returns:
    - Success message
    """
    # Convert IDs to UUID
    try:
        patient_uuid = uuid.UUID(patient_id)
        record_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Query for the specific record
    record = db.execute(
        select(HealthRecord).where(
            and_(
                HealthRecord.id == record_uuid,
                HealthRecord.patient_id == patient_uuid
            )
        )
    ).scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Health record {record_id} not found for patient {patient_id}"
        )
    
    db.delete(record)
    db.commit()
    
    return {
        "status": "DELETED",
        "recordId": record_id,
        "message": f"Health record {record_id} deleted successfully"
    }


@router.get("/{patient_id}/by-type/{record_type}", response_model=List[HealthRecordResponse])
async def get_records_by_type(
    patient_id: str,
    record_type: str,
    db: Session = Depends(get_db)
):
    """
    Get all health records of a specific type for a patient.
    
    Path Parameters:
    - patient_id: Patient identifier
    - record_type: Type of record (PRESCRIPTION, DIAGNOSTIC_REPORT, LAB_REPORT, etc.)
    
    Returns:
    - List of health records of the specified type
    """
    records = await get_health_records_for_patient(
        db=db,
        patient_id=patient_id,
        record_type=record_type
    )
    
    if not records:
        # Check if patient exists
        try:
            patient_uuid = uuid.UUID(patient_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient ID format")
        
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient {patient_id} not found"
            )
        
        return []
    
    return records


@router.get("/{patient_id}/from-hospital/{hospital_id}", response_model=List[HealthRecordResponse])
async def get_records_from_hospital(
    patient_id: str,
    hospital_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all health records received from a specific hospital.
    
    Path Parameters:
    - patient_id: Patient identifier
    - hospital_id: Source hospital bridge ID
    
    Returns:
    - List of health records from the specified hospital
    """
    records = await get_health_records_for_patient(
        db=db,
        patient_id=patient_id,
        source_hospital=hospital_id
    )
    
    if not records:
        # Check if patient exists
        try:
            patient_uuid = uuid.UUID(patient_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient ID format")
        
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient {patient_id} not found"
            )
        
        return []
    
    return records


# ============================================================================
# Additional Helper Endpoints
# ============================================================================

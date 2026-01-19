"""
Health data service for ABDM Hospital.
Handles storage, retrieval, and management of health records.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.database.models import HealthRecord, Patient
from app.utils.encryption import decrypt_health_data


async def get_mock_health_records(
    patient_id: str,
    data_types: List[str],
    care_context_ids: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate mock health records for a patient.
    Used by HIP to respond to data requests.
    
    Args:
        patient_id: Patient identifier
        data_types: Types of records to fetch (e.g., ["PRESCRIPTION", "DIAGNOSTIC_REPORT"])
        care_context_ids: Optional list of care context IDs to filter by
        
    Returns:
        List of mock health record objects
    """
    records = []
    
    if "PRESCRIPTION" in data_types:
        records.append({
            "type": "PRESCRIPTION",
            "date": "2026-01-15",
            "careContextId": care_context_ids[0] if care_context_ids else "cc-001",
            "medicines": [
                {
                    "name": "Amoxicillin",
                    "dosage": "500mg",
                    "frequency": "Twice daily",
                    "duration": "7 days"
                },
                {
                    "name": "Vitamin D3",
                    "dosage": "1000 IU",
                    "frequency": "Once daily",
                    "duration": "30 days"
                }
            ],
            "prescribedBy": "Dr. Sharma",
            "notes": "Take with food"
        })
    
    if "DIAGNOSTIC_REPORT" in data_types:
        records.append({
            "type": "DIAGNOSTIC_REPORT",
            "date": "2026-01-14",
            "careContextId": care_context_ids[0] if care_context_ids else "cc-001",
            "testName": "Complete Blood Count",
            "testCode": "CBC",
            "results": {
                "hemoglobin": {"value": 14.2, "unit": "g/dL", "status": "NORMAL"},
                "whiteBloodCells": {"value": 7.5, "unit": "K/uL", "status": "NORMAL"},
                "platelets": {"value": 250, "unit": "K/uL", "status": "NORMAL"}
            },
            "testedBy": "Pathology Lab A",
            "testedDate": "2026-01-14"
        })
    
    if "LAB_REPORT" in data_types:
        records.append({
            "type": "LAB_REPORT",
            "date": "2026-01-10",
            "careContextId": care_context_ids[0] if care_context_ids else "cc-001",
            "testName": "Blood Sugar Level",
            "result": "120 mg/dL",
            "status": "ELEVATED",
            "labName": "Apollo Diagnostics",
            "referenceRange": "70-100 mg/dL"
        })
    
    if "IMMUNIZATION" in data_types:
        records.append({
            "type": "IMMUNIZATION",
            "date": "2026-01-05",
            "careContextId": care_context_ids[0] if care_context_ids else "cc-001",
            "vaccines": [
                {
                    "name": "COVID-19",
                    "dose": "Dose 3 (Booster)",
                    "date": "2026-01-05",
                    "manufacturer": "Covaxin"
                }
            ],
            "administeredBy": "Hospital Vaccination Center"
        })
    
    return records


async def store_received_health_data(
    db: Session,
    patient_id: str,
    records: List[Dict[str, Any]],
    source_hospital: str,
    request_id: str = None
) -> bool:
    """
    Store health records received from another hospital via gateway.
    
    Args:
        db: Database session
        patient_id: Patient identifier
        records: List of health records received
        source_hospital: Bridge ID of source hospital
        request_id: Gateway request ID for tracking
        
    Returns:
        True if all records were stored successfully
    """
    try:
        # Convert patient_id to UUID
        patient_uuid = uuid.UUID(patient_id)
        
        # Get patient
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        if not patient:
            print(f"⚠️  Patient {patient_id} not found in database")
            return False
        
        stored_count = 0
        
        for record_data in records:
            record_type = record_data.get("type", "UNKNOWN")
            
            health_record = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient_uuid,
                record_type=record_type,
                record_date=datetime.fromisoformat(record_data.get("date", datetime.now(timezone.utc).isoformat())),
                data_json=record_data,
                source_hospital=source_hospital,
                request_id=request_id,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=1,
                last_delivery_timestamp=datetime.now(timezone.utc)
            )
            
            db.add(health_record)
            stored_count += 1
        
        db.commit()
        print(f"✅ Stored {stored_count} health records for patient {patient_id} from {source_hospital}")
        return True
        
    except Exception as e:
        print(f"❌ Error storing health records: {str(e)}")
        db.rollback()
        return False


async def decrypt_and_store_health_data(
    db: Session,
    patient_id: str,
    encrypted_data: str,
    source_hospital: str,
    request_id: str = None,
    jwt_secret: str = None
) -> bool:
    """
    Decrypt health data received from gateway and store it.
    
    Args:
        db: Database session
        patient_id: Patient identifier
        encrypted_data: Encrypted data from gateway webhook
        source_hospital: Bridge ID of source hospital
        request_id: Gateway request ID
        jwt_secret: Optional JWT secret for decryption
        
    Returns:
        True if decryption and storage successful
    """
    try:
        # Decrypt the data
        decrypted_data = decrypt_health_data(encrypted_data, jwt_secret)
        
        # Extract records from decrypted data
        records = decrypted_data.get("records", [])
        
        if not records:
            print(f"⚠️  No records found in decrypted data")
            return False
        
        # Store the decrypted records
        return await store_received_health_data(
            db=db,
            patient_id=patient_id,
            records=records,
            source_hospital=source_hospital,
            request_id=request_id
        )
        
    except Exception as e:
        print(f"❌ Error decrypting and storing health data: {str(e)}")
        return False


async def get_health_records_for_patient(
    db: Session,
    patient_id: str,
    record_type: str = None,
    source_hospital: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieve health records for a patient.
    
    Args:
        db: Database session
        patient_id: Patient identifier
        record_type: Optional filter by record type
        source_hospital: Optional filter by source hospital
        
    Returns:
        List of health records
    """
    try:
        # Convert patient_id to UUID
        patient_uuid = uuid.UUID(patient_id)
        
        # Get patient info
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        query = select(HealthRecord).where(HealthRecord.patient_id == patient_uuid)
        
        if record_type:
            query = query.where(HealthRecord.record_type == record_type)
        
        if source_hospital:
            query = query.where(HealthRecord.source_hospital == source_hospital)
        
        query = query.order_by(HealthRecord.record_date.desc())
        
        results = db.execute(query).scalars().all()
        
        return [
            {
                "id": str(record.id),
                "type": record.record_type,
                "date": record.record_date.isoformat(),
                "sourceHospital": record.source_hospital,
                "data": record.data_json,
                "receivedAt": record.created_at.isoformat(),
                # Additional fields for frontend
                "patientId": str(patient.id) if patient else patient_id,
                "patientName": patient.name if patient else "Unknown",
                "title": record.data_json.get("testName") or record.data_json.get("reportType") or f"{record.record_type} Record"
            }
            for record in results
        ]
        
    except Exception as e:
        print(f"❌ Error retrieving health records: {str(e)}")
        return []


async def get_external_health_records(
    db: Session,
    patient_id: str
) -> List[Dict[str, Any]]:
    """
    Get only health records received from other hospitals.
    
    Args:
        db: Database session
        patient_id: Patient identifier
        
    Returns:
        List of external health records
    """
    try:
        # Convert patient_id to UUID
        patient_uuid = uuid.UUID(patient_id)
        
        results = db.execute(
            select(HealthRecord).where(
                and_(
                    HealthRecord.patient_id == patient_uuid,
                    HealthRecord.source_hospital.isnot(None)
                )
            ).order_by(HealthRecord.record_date.desc())
        ).scalars().all()
        
        return [
            {
                "id": str(record.id),
                "type": record.record_type,
                "date": record.record_date.isoformat(),
                "sourceHospital": record.source_hospital,
                "data": record.data_json,
                "receivedAt": record.created_at.isoformat(),
                "requestId": record.request_id
            }
            for record in results
        ]
        
    except Exception as e:
        print(f"❌ Error retrieving external health records: {str(e)}")
        return []


async def get_health_record_summary(
    db: Session,
    patient_id: str
) -> Dict[str, Any]:
    """
    Get summary of all health records for a patient.
    
    Args:
        db: Database session
        patient_id: Patient identifier
        
    Returns:
        Summary with counts by type and source
    """
    try:
        all_records = await get_health_records_for_patient(db, patient_id)
        
        summary = {
            "totalRecords": len(all_records),
            "byType": {},
            "bySource": {},
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
        
        for record in all_records:
            # Count by type
            record_type = record.get("type")
            summary["byType"][record_type] = summary["byType"].get(record_type, 0) + 1
            
            # Count by source - convert None to "LOCAL"
            source = record.get("sourceHospital") or "LOCAL"
            summary["bySource"][source] = summary["bySource"].get(source, 0) + 1
        
        return summary
        
    except Exception as e:
        print(f"❌ Error generating health record summary: {str(e)}")
        return {"totalRecords": 0, "byType": {}, "bySource": {}}

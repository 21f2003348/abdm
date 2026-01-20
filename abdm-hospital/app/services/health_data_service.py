"""
Health data service for ABDM Hospital.
Handles storage, retrieval, and management of health records.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.database.models import HealthRecord, Patient, CareContext
from app.utils.encryption import decrypt_health_data
from app.services.gateway_service import link_care_contexts_to_gateway


def _get_or_create_patient_by_identifier(db: Session, patient_identifier: str) -> Optional[Patient]:
    """Resolve patient by UUID or ABHA; create stub if missing."""
    try:
        patient_uuid = uuid.UUID(patient_identifier)
        patient = db.execute(select(Patient).where(Patient.id == patient_uuid)).scalar_one_or_none()
        if patient:
            return patient
    except Exception:
        patient_uuid = None

    # Try ABHA match
    patient = db.execute(select(Patient).where(Patient.abha_id == patient_identifier)).scalar_one_or_none()
    if patient:
        return patient

    # Auto-create minimal patient record to avoid losing incoming data
    patient = Patient(
        id=patient_uuid or uuid.uuid4(),
        name=f"Patient {patient_identifier}",
        mobile=None,
        abha_id=patient_identifier,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def ensure_patient_has_abha_id(db: Session, patient_uuid: uuid.UUID) -> Optional[str]:
    """
    Ensure patient has an ABHA ID, generate one if missing.
    Critical for gateway linking since gateway uses ABHA ID as patient identifier.
    
    Args:
        db: Database session
        patient_uuid: Patient UUID (local DB identifier)
        
    Returns:
        Patient ABHA ID or None if patient not found
    """
    try:
        patient = db.execute(
            select(Patient).where(Patient.id == patient_uuid)
        ).scalar_one_or_none()
        
        if not patient:
            print(f"❌ Patient {patient_uuid} not found")
            return None
        
        # If patient already has ABHA ID, return it
        if patient.abha_id:
            print(f"✓ Patient already has ABHA ID: {patient.abha_id}")
            return patient.abha_id
        
        # Generate new ABHA ID if missing
        # Format: patient-{first_3_chars_of_name}-{uuid_short}@abdm
        name_prefix = patient.name.split()[0][:3].lower() if patient.name else "pat"
        short_uuid = str(patient_uuid)[:8].lower()
        new_abha_id = f"patient-{name_prefix}-{short_uuid}@abdm"
        
        # Ensure uniqueness by checking if this ABHA ID already exists
        existing = db.execute(
            select(Patient).where(Patient.abha_id == new_abha_id)
        ).scalar_one_or_none()
        
        if existing:
            # Add timestamp suffix for uniqueness
            from datetime import datetime
            timestamp = int(datetime.utcnow().timestamp()) % 10000
            new_abha_id = f"patient-{name_prefix}-{short_uuid}-{timestamp}@abdm"
        
        patient.abha_id = new_abha_id
        db.commit()
        db.refresh(patient)
        
        print(f"✓ Generated new ABHA ID for patient: {new_abha_id}")
        return new_abha_id
        
    except Exception as e:
        print(f"❌ Error ensuring patient ABHA ID: {str(e)}")
        return None


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
    patient_identifier: str,
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
        patient = _get_or_create_patient_by_identifier(db, patient_identifier)
        if not patient:
            print(f"⚠️  Patient {patient_identifier} not found and could not be created")
            return False
        
        stored_count = 0
        
        for record_data in records:
            record_type = record_data.get("type", "UNKNOWN")
            
            health_record = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
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
        print(f"✅ Stored {stored_count} health records for patient {patient_identifier} from {source_hospital}")
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
            patient_identifier=patient_id,
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
    Get health records for a patient by UUID.
    This is the primary method for local queries.
    
    Args:
        db: Database session
        patient_id: Patient UUID or ABHA ID
        record_type: Optional filter by record type
        source_hospital: Optional filter by source hospital
        
    Returns:
        List of health records
    """
    try:
        patient_uuid = None
        patient = None
        
        # First try UUID
        try:
            patient_uuid = uuid.UUID(patient_id)
            query = select(HealthRecord).where(HealthRecord.patient_id == patient_uuid)
        except ValueError:
            # If not UUID, try to find by ABHA ID
            patient = db.execute(
                select(Patient).where(Patient.abha_id == patient_id)
            ).scalar_one_or_none()
            
            if not patient:
                return []
            
            patient_uuid = patient.id
            query = select(HealthRecord).where(HealthRecord.patient_id == patient.id)
        
        # Get patient info if not already fetched
        if not patient:
            patient = db.execute(select(Patient).where(Patient.id == patient_uuid)).scalar_one_or_none()
        
        # Apply optional filters
        if record_type:
            query = query.where(HealthRecord.record_type == record_type)
        
        if source_hospital:
            query = query.where(HealthRecord.source_hospital == source_hospital)
        
        records = db.execute(query).scalars().all()
        
        result = []
        for record in records:
            data = record.data_json or {}
            
            # Try to find care context for this record (by naming convention)
            context_name = f"{record.record_type}_{record.record_date.date().isoformat()}_{str(record.id)[:8]}"
            care_context = db.execute(
                select(CareContext).where(
                    and_(
                        CareContext.patient_id == record.patient_id,
                        CareContext.context_name == context_name
                    )
                )
            ).scalar_one_or_none()
            care_context_id = str(care_context.id) if care_context else None
            
            # Extract visit_id from data_json if present
            visit_id = data.get('visitId') or data.get('visit_id')
            
            result.append({
                "id": str(record.id),
                "type": record.record_type,
                "date": record.record_date,
                "sourceHospital": record.source_hospital,
                "data": data,
                "receivedAt": record.created_at,
                "requestId": record.request_id,
                "patientId": str(record.patient_id),
                "patientName": patient.name if patient else None,
                "title": data.get("title") or record.record_type,
                "doctor_name": data.get("doctorName") or data.get("doctor_name"),
                "department": data.get("department"),
                "content": data.get("content") or record.data_text,
                "visitId": visit_id,
                "visit_id": visit_id,  # For backward compatibility
                "careContextId": care_context_id,
                "care_context_id": care_context_id,  # For backward compatibility
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            })
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting health records: {str(e)}")
        return []


async def get_patient_complete_history(
    db: Session,
    patient_identifier: str
) -> Dict[str, Any]:
    """
    Get complete patient history including local and externally received records.
    This is the unified method that works with both UUID and ABHA ID.
    
    Args:
        db: Database session
        patient_identifier: Either patient UUID or ABHA ID
        
    Returns:
        Dictionary with:
        - patient: Patient details with both UUID and ABHA ID
        - localRecords: Records created locally
        - externalRecords: Records received from other hospitals
        - allRecords: All records combined
        - summary: Summary statistics
    """
    try:
        # Resolve patient by UUID or ABHA ID
        patient_uuid = None
        patient_abha = None
        
        try:
            patient_uuid = uuid.UUID(patient_identifier)
        except ValueError:
            patient_abha = patient_identifier
        
        # Query patient
        if patient_uuid:
            patient = db.execute(
                select(Patient).where(Patient.id == patient_uuid)
            ).scalar_one_or_none()
        else:
            patient = db.execute(
                select(Patient).where(Patient.abha_id == patient_abha)
            ).scalar_one_or_none()
        
        if not patient:
            return {
                "patient": None,
                "localRecords": [],
                "externalRecords": [],
                "allRecords": [],
                "summary": {"totalRecords": 0, "byType": {}, "bySource": {}},
                "error": f"Patient not found: {patient_identifier}"
            }
        
        # Get all records for this patient
        all_records = db.execute(
            select(HealthRecord).where(HealthRecord.patient_id == patient.id)
        ).scalars().all()
        
        # Separate local and external records
        local_records = []
        external_records = []
        record_types = {}
        source_hospitals = {}
        
        for record in all_records:
            record_dict = {
                "id": str(record.id),
                "type": record.record_type,
                "date": record.record_date.isoformat(),
                "sourceHospital": record.source_hospital,
                "data": record.data_json,
                "receivedAt": record.created_at.isoformat(),
                "requestId": record.request_id
            }
            
            if record.source_hospital:
                external_records.append(record_dict)
                source_hospitals[record.source_hospital] = source_hospitals.get(record.source_hospital, 0) + 1
            else:
                local_records.append(record_dict)
            
            record_types[record.record_type] = record_types.get(record.record_type, 0) + 1
        
        return {
            "patient": {
                "id": str(patient.id),
                "uuid": str(patient.id),  # Explicit for clarity
                "abhaId": patient.abha_id,
                "name": patient.name,
                "mobile": patient.mobile
            },
            "localRecords": local_records,
            "externalRecords": external_records,
            "allRecords": local_records + external_records,
            "summary": {
                "totalRecords": len(all_records),
                "localCount": len(local_records),
                "externalCount": len(external_records),
                "byType": record_types,
                "bySource": source_hospitals,
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting patient complete history: {str(e)}")
        return {
            "patient": None,
            "localRecords": [],
            "externalRecords": [],
            "allRecords": [],
            "summary": {"totalRecords": 0, "byType": {}, "bySource": {}},
            "error": str(e)
        }

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


async def create_care_context_for_record(
    db: Session,
    patient_id: uuid.UUID,
    record_id: uuid.UUID,
    record_type: str,
    record_date: str
) -> Optional[Dict[str, Any]]:
    """
    Auto-create a care context for a newly created health record and link it to the gateway.
    
    Args:
        db: Database session
        patient_id: Patient UUID
        record_id: Health record UUID
        record_type: Type of record (PRESCRIPTION, DIAGNOSTIC_REPORT, etc.)
        record_date: Date of the record
        
    Returns:
        Dictionary with care context and gateway linking status
    """
    try:
        # Get patient details
        patient = db.execute(
            select(Patient).where(Patient.id == patient_id)
        ).scalar_one_or_none()
        
        if not patient:
            print(f"❌ Patient {patient_id} not found for care context creation")
            return None
        
        # Create a meaningful care context name
        context_name = f"{record_type}_{record_date}_{str(record_id)[:8]}"
        description = f"Auto-created for {record_type} on {record_date}"
        
        # Check if care context already exists for this record
        existing_context = db.execute(
            select(CareContext).where(
                and_(
                    CareContext.patient_id == patient_id,
                    CareContext.context_name == context_name
                )
            )
        ).scalar_one_or_none()
        
        if existing_context:
            print(f"✓ Care context already exists: {existing_context.id}")
            return {
                "careContext": {
                    "id": str(existing_context.id),
                    "name": existing_context.context_name,
                    "description": existing_context.description
                },
                "alreadyExists": True
            }
        
        # Create new care context
        new_context = CareContext(
            id=uuid.uuid4(),
            patient_id=patient_id,
            context_name=context_name,
            description=description
        )
        
        db.add(new_context)
        db.commit()
        db.refresh(new_context)
        
        print(f"✓ Created care context: {new_context.id} for record {record_id}")
        
        # Link to gateway if patient has ABHA ID
        gateway_response = None
        if patient.abha_id:
            try:
                from app.services.gateway_service import TokenManager, generate_link_token, init_link
                
                # Step 1: Create linking request in gateway (creates LinkingRequest row)
                bridge_id = TokenManager.get_bridge_details()[0]
                try:
                    link_token_resp = await generate_link_token(patient.abha_id)
                    txn_id = None
                    if isinstance(link_token_resp, dict):
                        txn_id = link_token_resp.get("txnId")
                    
                    if txn_id:
                        await init_link({
                            "patientId": patient.abha_id,
                            "txnId": txn_id,
                            "hipId": bridge_id,
                        })
                        print(f"✓ Linking request created/linked in gateway: txnId={txn_id}")
                    else:
                        print(f"⚠️  Link token generation did not return txnId: {link_token_resp}")
                except Exception as e:
                    # Non-fatal: care context linking can still proceed
                    print(f"⚠️  Failed to create linking request in gateway: {str(e)}")
                
                # Step 2: Link care context to gateway
                payload = {
                    "patientId": patient.abha_id,
                    "careContextId": str(new_context.id),
                    "contextName": context_name,
                    "referenceNumber": context_name,
                    "hipId": bridge_id
                }
                
                gateway_response = await link_care_contexts_to_gateway(payload)
                print(f"✓ Linked care context {new_context.id} to gateway for patient {patient.abha_id}")
                
            except Exception as e:
                print(f"⚠️  Failed to link care context to gateway: {str(e)}")
                gateway_response = {"error": str(e), "status": "FAILED"}
        else:
            print(f"⚠️  Patient has no ABHA ID, skipping gateway linking")
            gateway_response = {"status": "SKIPPED", "reason": "No ABHA ID"}
        
        return {
            "careContext": {
                "id": str(new_context.id),
                "name": new_context.context_name,
                "description": new_context.description
            },
            "gatewayLinking": gateway_response,
            "created": True
        }
        
    except Exception as e:
        print(f"❌ Error creating care context for record: {str(e)}")
        db.rollback()
        return {"error": str(e), "created": False}

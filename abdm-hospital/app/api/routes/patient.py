from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database.models import Patient

router = APIRouter()

# Models
class PatientRegistrationRequest(BaseModel):
    name: str
    mobile: str
    abhaId: Optional[str] = None
    abhaAddress: Optional[str] = None
    aadhaar: Optional[str] = None
    gender: Optional[str] = None  # Male, Female, Other
    dateOfBirth: Optional[str] = None  # ISO format date string

class PatientResponse(BaseModel):
    patientId: str
    name: str
    mobile: str
    abhaId: Optional[str]
    abhaAddress: Optional[str] = None
    gatewayPatientId: Optional[str] = None
    aadhaar: Optional[str] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[str] = None

# Database Logic (Placeholder)
def find_patient_by_mobile(db: Session, mobile: str):
    """Query the database to find a patient by mobile number."""
    result = db.execute(select(Patient).where(Patient.mobile == mobile)).scalar_one_or_none()
    if result:
        return {
            "patientId": str(result.id),
            "name": result.name,
            "mobile": result.mobile,
            "abhaId": result.abha_id,
            "gatewayPatientId": result.gateway_patient_id,
            "aadhaar": result.aadhaar,
            "gender": result.gender,
            "dateOfBirth": result.date_of_birth.isoformat() if result.date_of_birth else None
        }
    return None

def create_new_patient(db: Session, patient_data: PatientRegistrationRequest, gateway_patient_id: str = None):
    """Insert a new patient into the database."""
    try:
        from datetime import datetime
        # Debug log: received gender/dateOfBirth
        print(f"[DEBUG][backend] create_new_patient received gender: {patient_data.gender}, dateOfBirth: {patient_data.dateOfBirth}")
        # Treat empty strings as None
        gender = patient_data.gender if patient_data.gender else None
        dob_str = patient_data.dateOfBirth if patient_data.dateOfBirth else None
        # Parse date_of_birth if provided
        from datetime import datetime
        date_of_birth = None
        if dob_str:
            try:
                if "T" in dob_str:
                    # ISO datetime (2024-01-01T00:00:00Z)
                    date_of_birth = datetime.fromisoformat(dob_str.replace("Z", "+00:00"))
                else:
                    # Date-only (2024-01-01)
                    date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d")
            except ValueError as e:
                print(f"[ERROR] Invalid dateOfBirth format: {dob_str}, error: {e}")
        new_patient = Patient(
            name=patient_data.name,
            mobile=patient_data.mobile,
            abha_id=patient_data.abhaId,
            abha_address=getattr(patient_data, 'abhaAddress', None),
            gateway_patient_id=gateway_patient_id,
            aadhaar=patient_data.aadhaar,
            gender=gender,
            date_of_birth=date_of_birth
        )
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        # Debug log: after DB insert
        print(f"[DEBUG][backend] Stored gender: {new_patient.gender}, date_of_birth: {new_patient.date_of_birth}")
        return {
            "patientId": str(new_patient.id),
            "name": new_patient.name,
            "mobile": new_patient.mobile,
            "abhaId": new_patient.abha_id,
            "abhaAddress": new_patient.abha_address,
            "gatewayPatientId": new_patient.gateway_patient_id,
            "aadhaar": new_patient.aadhaar,
            "gender": new_patient.gender,
            "dateOfBirth": new_patient.date_of_birth.isoformat() if new_patient.date_of_birth else None
        }
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig)
        if "aadhaar" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="A patient with this Aadhaar number already exists"
            )
        elif "abha_id" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="A patient with this ABHA ID already exists"
            )
        elif "mobile" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="A patient with this mobile number already exists"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="A patient with these details already exists"
            )

# Endpoints
@router.post("/api/patient/register", response_model=PatientResponse)
async def register_patient(
    request: PatientRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register a new patient or identify an existing one."""
    # Debug: Print received gender and dateOfBirth
    print(f"[DEBUG][backend] register_patient received gender: {request.gender}, dateOfBirth: {request.dateOfBirth}")
    # Check for existing patient by ABHA ID first (if provided)
    if request.abhaId:
        existing_by_abha = db.execute(
            select(Patient).where(Patient.abha_id == request.abhaId)
        ).scalar_one_or_none()
        
        if existing_by_abha:
            return {
                "patientId": str(existing_by_abha.id),
                "name": existing_by_abha.name,
                "mobile": existing_by_abha.mobile,
                "abhaId": existing_by_abha.abha_id,
                "aadhaar": existing_by_abha.aadhaar,
                "gender": existing_by_abha.gender,
                "dateOfBirth": existing_by_abha.date_of_birth.isoformat() if existing_by_abha.date_of_birth else None,
                "gatewayPatientId": existing_by_abha.gateway_patient_id,
                "message": "Patient already registered with this ABHA ID"
            }
    
    # Check for existing patient by Aadhaar (if provided)
    if request.aadhaar:
        existing_by_aadhaar = db.execute(
            select(Patient).where(Patient.aadhaar == request.aadhaar)
        ).scalar_one_or_none()
        
        if existing_by_aadhaar:
            # Patient exists with same Aadhaar, update ABHA ID if provided and not set
            if request.abhaId and not existing_by_aadhaar.abha_id:
                existing_by_aadhaar.abha_id = request.abhaId
                db.commit()
                db.refresh(existing_by_aadhaar)
            
            return {
                "patientId": str(existing_by_aadhaar.id),
                "name": existing_by_aadhaar.name,
                "mobile": existing_by_aadhaar.mobile,
                "abhaId": existing_by_aadhaar.abha_id,
                "aadhaar": existing_by_aadhaar.aadhaar,
                "gender": existing_by_aadhaar.gender,
                "dateOfBirth": existing_by_aadhaar.date_of_birth.isoformat() if existing_by_aadhaar.date_of_birth else None,
                "gatewayPatientId": existing_by_aadhaar.gateway_patient_id,
                "message": "Patient already registered with this Aadhaar number"
            }
    
    # Check by mobile number
    existing_patient = find_patient_by_mobile(db, request.mobile)
    if existing_patient:
        return existing_patient
    
    # Step 1: First register with gateway to get gateway_patient_id
    gateway_patient_id = None
    gateway_abha_id = None
    gateway_abha_address = None
    gateway_result = None
    
    try:
        from app.services.gateway_service import discover_patient
        from datetime import datetime
        
        # Prepare gateway payload with all available data
        gateway_payload = {
            "mobile": request.mobile,
            "name": request.name
        }
        
        # Add optional fields
        if request.gender:
            gateway_payload["gender"] = request.gender
        if request.dateOfBirth:
            gateway_payload["dateOfBirth"] = request.dateOfBirth
        if request.aadhaar:
            gateway_payload["aadhaar"] = request.aadhaar
        
        # Call gateway discover endpoint
        gateway_result = await discover_patient(gateway_payload)
        if isinstance(gateway_result, dict):
            gateway_patient_id = gateway_result.get("patientId")
            gateway_abha_id = gateway_result.get("abhaId") or request.abhaId
            gateway_abha_address = gateway_result.get("abhaAddress")
            print(f"✓ Patient registered with gateway: {gateway_patient_id}")
        else:
            print(f"⚠️ Gateway returned empty or invalid response: {gateway_result!r}")
            
    except Exception as e:
        print(f"⚠️ Gateway registration failed (non-critical): {str(e)}")
        # Continue with local registration even if gateway fails
    
    # Step 2: Create new patient in local DB with gateway_patient_id
    # Prepare all gateway fields for Patient
    update_fields = {}
    if gateway_abha_id:
        update_fields["abhaId"] = gateway_abha_id
    if gateway_abha_address:
        update_fields["abhaAddress"] = gateway_abha_address
    if isinstance(gateway_result, dict):
        if gateway_result.get("gender"):
            update_fields["gender"] = gateway_result.get("gender")
        if gateway_result.get("dateOfBirth"):
            update_fields["dateOfBirth"] = gateway_result.get("dateOfBirth")
    patient_data = request.copy(update=update_fields)
    new_patient = create_new_patient(db, patient_data, gateway_patient_id=gateway_patient_id)

    # Update Patient object in DB with any missing gateway fields
    import uuid
    patient_uuid = new_patient["patientId"]
    if isinstance(patient_uuid, str):
        try:
            patient_uuid = uuid.UUID(patient_uuid)
        except Exception:
            pass
    patient_obj = db.execute(
        select(Patient).where(Patient.id == patient_uuid)
    ).scalar_one_or_none()
    if patient_obj:
        updated = False
        if gateway_abha_id and not patient_obj.abha_id:
            patient_obj.abha_id = gateway_abha_id
            new_patient["abhaId"] = gateway_abha_id
            updated = True
        if gateway_abha_address and not patient_obj.abha_address:
            patient_obj.abha_address = gateway_abha_address
            new_patient["abhaAddress"] = gateway_abha_address
            updated = True
        if gateway_result:
            if gateway_result.get("gender") and not patient_obj.gender:
                patient_obj.gender = gateway_result.get("gender")
                new_patient["gender"] = gateway_result.get("gender")
                updated = True
            if gateway_result.get("dateOfBirth") and not patient_obj.date_of_birth:
                from datetime import datetime
                try:
                    patient_obj.date_of_birth = datetime.fromisoformat(gateway_result.get("dateOfBirth"))
                    new_patient["dateOfBirth"] = gateway_result.get("dateOfBirth")
                    updated = True
                except:
                    pass
        if updated:
            db.commit()
            db.refresh(patient_obj)
            # Debug log: after DB update
            print(f"[DEBUG][backend] Updated gender: {patient_obj.gender}, date_of_birth: {patient_obj.date_of_birth}")
    new_patient["message"] = "Patient registered successfully" + (" and synced with gateway" if gateway_patient_id else "")
    return new_patient

@router.get("/api/patient/list", response_model=List[PatientResponse])
def list_patients(db: Session = Depends(get_db)):
    """Get all registered patients."""
    patients = db.execute(select(Patient)).scalars().all()
    return [
        {
            "patientId": str(patient.id),
            "name": patient.name,
            "mobile": patient.mobile,
            "abhaId": patient.abha_id,
            "abhaAddress": getattr(patient, "abha_address", None),
            "aadhaar": patient.aadhaar,
            "gatewayPatientId": patient.gateway_patient_id,
            "gender": patient.gender,
            "dateOfBirth": patient.date_of_birth.isoformat() if patient.date_of_birth else None
        }
        for patient in patients
    ]
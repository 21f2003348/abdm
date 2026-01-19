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
    aadhaar: Optional[str] = None

class PatientResponse(BaseModel):
    patientId: str
    name: str
    mobile: str
    abhaId: Optional[str]
    aadhaar: Optional[str] = None

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
            "aadhaar": result.aadhaar
        }
    return None

def create_new_patient(db: Session, patient_data: PatientRegistrationRequest):
    """Insert a new patient into the database."""
    try:
        new_patient = Patient(
            name=patient_data.name,
            mobile=patient_data.mobile,
            abha_id=patient_data.abhaId,
            aadhaar=patient_data.aadhaar
        )
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        return {
            "patientId": str(new_patient.id),
            "name": new_patient.name,
            "mobile": new_patient.mobile,
            "abhaId": new_patient.abha_id,
            "aadhaar": new_patient.aadhaar
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
def register_patient(
    request: PatientRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register a new patient or identify an existing one."""
    existing_patient = find_patient_by_mobile(db, request.mobile)
    if existing_patient:
        return existing_patient
    new_patient = create_new_patient(db, request)
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
            "aadhaar": patient.aadhaar
        }
        for patient in patients
    ]
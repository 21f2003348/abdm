from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from pydantic import BaseModel
from typing import Optional, List
from app.database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models import Visit, Patient
import uuid
from datetime import datetime
from app.services import gateway_service
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ...existing code...

# PATCH endpoint to update visit status
@router.patch("/api/visit/{visit_id}/status")
def update_visit_status(visit_id: str, status: str = Body(...), db: Session = Depends(get_db)):
    visit_uuid = uuid.UUID(visit_id)
    visit = db.query(Visit).filter(Visit.id == visit_uuid).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.status = status
    db.commit()
    db.refresh(visit)
    return {
        "visitId": str(visit.id),
        "status": visit.status
    }
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from pydantic import BaseModel
from typing import Optional, List
from app.database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models import Visit, Patient
import uuid
from datetime import datetime
from app.services import gateway_service
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
# PATCH endpoint to update visit status
@router.patch("/api/visit/{visit_id}/status")
def update_visit_status(visit_id: str, status: str = Body(...), db: Session = Depends(get_db)):
    visit_uuid = uuid.UUID(visit_id)
    visit = db.query(Visit).filter(Visit.id == visit_uuid).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.status = status
    db.commit()
    db.refresh(visit)
    return {
        "visitId": str(visit.id),
        "status": visit.status
    }

# Models
class VisitRequest(BaseModel):
    patientId: str
    visitType: str
    department: str
    doctorId: Optional[str] = None
    visitDate: str
    status: Optional[str] = "Scheduled"

class VisitResponse(BaseModel):
    visitId: str
    patientId: str
    visitType: str
    department: str
    doctorId: Optional[str]
    visitDate: str
    status: str
    patientName: Optional[str] = None

# Database Logic (Placeholder)
def create_new_visit(db: Session, visit_data: VisitRequest):
    """Insert a new visit into the database."""
    visit_date = datetime.fromisoformat(visit_data.visitDate)  # Convert to datetime object

    new_visit = Visit(
        patient_id=uuid.UUID(visit_data.patientId),  # Convert to UUID
        visit_type=visit_data.visitType,
        department=visit_data.department,
        doctor_id=visit_data.doctorId,
        visit_date=visit_date,
        status=visit_data.status or "Scheduled"
    )
    db.add(new_visit)
    db.commit()
    db.refresh(new_visit)
    return {
        "visitId": str(new_visit.id),  # Ensure UUID is converted to string
        "patientId": str(new_visit.patient_id),  # Convert back to string for response
        "visitType": new_visit.visit_type,
        "department": new_visit.department,
        "doctorId": new_visit.doctor_id,
        "visitDate": new_visit.visit_date.isoformat(),  # Convert datetime to string for response
        "status": new_visit.status
    }

# Background task to create consent request in gateway
def create_consent_request(visit_id: str, patient_id: str, department: str, visit_type: str):
    """
    Background task to create consent request in ABDM Gateway for a visit.
    """
    try:
        from app.database.connection import SessionLocal
        from app.services.gateway_service import TokenManager, init_consent_request
        db = SessionLocal()
        
        logger.info(f"Creating consent request for visit {visit_id}")
        
        # Get patient details
        patient_uuid = uuid.UUID(patient_id)
        patient = db.query(Patient).filter(Patient.id == patient_uuid).first()
        
        if not patient:
            logger.error(f"Patient not found: {patient_id}")
            return
        
        if not patient.abha_id:
            logger.warning(f"Patient {patient_id} has no ABHA ID, skipping consent request creation")
            return
        
        # Get bridge ID
        try:
            bridge_id = TokenManager.get_bridge_details()[0]
        except Exception as e:
            logger.error(f"Failed to get bridge ID: {str(e)}")
            return
        
        # Create consent request in gateway
        purpose = {
            "code": "CAREMGT",
            "text": f"Care Management - {visit_type} visit for {department}"
        }
        
        consent_result = asyncio.run(init_consent_request(
            patient_id=patient.abha_id,
            hip_id=bridge_id,
            purpose=purpose
        ))
        
        if consent_result:
            consent_id = consent_result.get("consentRequestId")
            logger.info(f"Consent request created in gateway: {consent_id} for visit {visit_id}")
        else:
            logger.warning(f"Consent request creation returned empty result")
        
    except Exception as e:
        logger.error(f"Error creating consent request: {str(e)}")
    finally:
        db.close()

# Endpoints
@router.post("/api/visit/create", response_model=VisitResponse)
def create_visit(
    request: VisitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new visit and automatically create consent request in gateway."""
    new_visit = create_new_visit(db, request)
    
    # Add background task to create consent request in gateway
    background_tasks.add_task(
        create_consent_request,
        new_visit["visitId"],
        new_visit["patientId"],
        request.department,
        request.visitType
    )
    
    return new_visit

@router.get("/api/visit/list", response_model=List[VisitResponse])
def list_visits(db: Session = Depends(get_db)):
    """Get all visits."""
    visits = db.execute(select(Visit)).scalars().all()
    return [
        {
            "visitId": str(visit.id),
            "patientId": str(visit.patient_id),
            "visitType": visit.visit_type,
            "department": visit.department,
            "doctorId": visit.doctor_id,
            "visitDate": visit.visit_date.isoformat(),
            "status": visit.status
        }
        for visit in visits
    ]

@router.get("/api/visit/patient/{patient_id}", response_model=List[VisitResponse])
def get_visits_by_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get all visits for a specific patient."""
    patient_uuid = uuid.UUID(patient_id)
    visits = db.execute(select(Visit).where(Visit.patient_id == patient_uuid)).scalars().all()
    return [
        {
            "visitId": str(visit.id),
            "patientId": str(visit.patient_id),
            "visitType": visit.visit_type,
            "department": visit.department,
            "doctorId": visit.doctor_id,
            "visitDate": visit.visit_date.isoformat(),
            "status": visit.status
        }
        for visit in visits
    ]

@router.get("/api/visit/active", response_model=List[VisitResponse])
def get_active_visits(db: Session = Depends(get_db)):
    """Get all active visits (Scheduled or In Progress)."""
    from sqlalchemy import or_
    visits = db.execute(
        select(Visit).where(or_(Visit.status == "Scheduled", Visit.status == "In Progress"))
    ).scalars().all()
    
    # Include patient name for better display
    result = []
    for visit in visits:
        patient = db.execute(select(Patient).where(Patient.id == visit.patient_id)).scalar_one_or_none()
        result.append({
            "visitId": str(visit.id),
            "patientId": str(visit.patient_id),
            "patientName": patient.name if patient else "Unknown",
            "visitType": visit.visit_type,
            "department": visit.department,
            "doctorId": visit.doctor_id,
            "visitDate": visit.visit_date.isoformat(),
            "status": visit.status
        })
    return result
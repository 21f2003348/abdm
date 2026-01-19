from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.models import Visit, Patient, CareContext
import uuid
from datetime import datetime
from app.services import gateway_service
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

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

# Background task to create care context and link to gateway
def create_and_link_care_context(visit_id: str, patient_id: str, department: str, visit_type: str):
    """
    Background task to automatically create care context and link to ABDM Gateway.
    """
    try:
        from app.database.connection import SessionLocal
        db = SessionLocal()
        
        logger.info(f"Starting care context creation for visit {visit_id}")
        
        # Get patient details
        patient_uuid = uuid.UUID(patient_id)
        patient = db.query(Patient).filter(Patient.id == patient_uuid).first()
        
        if not patient:
            logger.error(f"Patient not found: {patient_id}")
            return
        
        # Create care context with department as name
        care_context_name = f"{department} Care - {datetime.now().year}"
        care_context = CareContext(
            id=uuid.uuid4(),
            patient_id=patient_uuid,
            context_name=care_context_name,
            description=f"{visit_type} visit for {department}"
        )
        db.add(care_context)
        db.commit()
        db.refresh(care_context)
        
        logger.info(f"Created care context: {care_context.id}")
        
        # Link care context to gateway asynchronously
        asyncio.run(link_care_context_to_gateway(
            patient.abha_id,
            str(care_context.id),
            care_context_name
        ))
        
        logger.info(f"Successfully linked care context to gateway: {care_context.id}")
        
    except Exception as e:
        logger.error(f"Error creating/linking care context: {str(e)}")
    finally:
        db.close()

async def link_care_context_to_gateway(patient_abha_id: str, care_context_id: str, context_name: str):
    """
    Link care context to ABDM Gateway.
    """
    try:
        from app.services.gateway_service import TokenManager
        
        bridge_id = TokenManager.get_bridge_details()[0]
        
        payload = {
            "patientId": patient_abha_id,
            "careContextId": care_context_id,
            "contextName": context_name,
            "referenceNumber": care_context_id,
            "hipId": bridge_id
        }
        
        logger.info(f"Linking care context to gateway with payload: {payload}")
        
        result = await gateway_service.link_care_contexts_to_gateway(payload)
        
        logger.info(f"Care context linked successfully: {result}")
        
    except Exception as e:
        logger.error(f"Failed to link care context to gateway: {str(e)}")

# Endpoints
@router.post("/api/visit/create", response_model=VisitResponse)
def create_visit(
    request: VisitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new visit and automatically create/link care context in background."""
    new_visit = create_new_visit(db, request)
    
    # Add background task to create and link care context
    background_tasks.add_task(
        create_and_link_care_context,
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
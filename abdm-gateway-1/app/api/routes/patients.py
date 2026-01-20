"""
Patient Management Routes for ABDM Gateway.
Handles patient registration and lookup in the central gateway registry.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.connection import get_db
from app.database.models import Patient
from app.deps.auth import verify_token

router = APIRouter(prefix="/api/patients", tags=["patients"])


class PatientRegisterRequest(BaseModel):
    abhaId: str
    abhaAddress: Optional[str] = None
    name: str
    mobile: Optional[str] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[str] = None


class PatientResponse(BaseModel):
    abhaId: str
    abhaAddress: Optional[str]
    name: str
    mobile: Optional[str]
    gender: Optional[str]
    dateOfBirth: Optional[str]
    createdAt: str
    updatedAt: str


@router.post("/register", response_model=PatientResponse)
async def register_patient(
    request: PatientRegisterRequest,
    db: AsyncSession = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    Register a new patient in the gateway's central registry.
    If patient already exists, returns existing record.
    
    This is called by hospitals when they link a patient's care context.
    """
    # Check if patient already exists
    result = await db.execute(
        select(Patient).where(Patient.abha_id == request.abhaId)
    )
    existing_patient = result.scalar_one_or_none()
    
    if existing_patient:
        # Update existing patient info if provided
        if request.name:
            existing_patient.name = request.name
        if request.mobile:
            existing_patient.mobile = request.mobile
        if request.gender:
            existing_patient.gender = request.gender
        if request.abhaAddress:
            existing_patient.abha_address = request.abhaAddress
        if request.dateOfBirth:
            existing_patient.date_of_birth = datetime.fromisoformat(request.dateOfBirth)
        
        existing_patient.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_patient)
        
        return PatientResponse(
            abhaId=existing_patient.abha_id,
            abhaAddress=existing_patient.abha_address,
            name=existing_patient.name,
            mobile=existing_patient.mobile,
            gender=existing_patient.gender,
            dateOfBirth=existing_patient.date_of_birth.isoformat() if existing_patient.date_of_birth else None,
            createdAt=existing_patient.created_at.isoformat(),
            updatedAt=existing_patient.updated_at.isoformat()
        )
    
    # Create new patient
    new_patient = Patient(
        abha_id=request.abhaId,
        abha_address=request.abhaAddress,
        name=request.name,
        mobile=request.mobile,
        gender=request.gender,
        date_of_birth=datetime.fromisoformat(request.dateOfBirth) if request.dateOfBirth else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    
    return PatientResponse(
        abhaId=new_patient.abha_id,
        abhaAddress=new_patient.abha_address,
        name=new_patient.name,
        mobile=new_patient.mobile,
        gender=new_patient.gender,
        dateOfBirth=new_patient.date_of_birth.isoformat() if new_patient.date_of_birth else None,
        createdAt=new_patient.created_at.isoformat(),
        updatedAt=new_patient.updated_at.isoformat()
    )


@router.get("/{abha_id}", response_model=PatientResponse)
async def get_patient(
    abha_id: str,
    db: AsyncSession = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    Get patient information by ABHA ID.
    """
    result = await db.execute(
        select(Patient).where(Patient.abha_id == abha_id)
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found in gateway registry")
    
    return PatientResponse(
        abhaId=patient.abha_id,
        abhaAddress=patient.abha_address,
        name=patient.name,
        mobile=patient.mobile,
        gender=patient.gender,
        dateOfBirth=patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        createdAt=patient.created_at.isoformat(),
        updatedAt=patient.updated_at.isoformat()
    )

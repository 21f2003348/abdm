import uuid
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import LinkingRequest, LinkedCareContext, Patient


async def _ensure_patient(
    db: AsyncSession,
    patient_abha_id: str,
    name: Optional[str] = None,
    mobile: Optional[str] = None,
) -> Patient:
    """Fetch or auto-register a patient by ABHA ID on first sight."""
    result = await db.execute(select(Patient).where(Patient.abha_id == patient_abha_id))
    patient = result.scalar_one_or_none()

    if patient:
        if name:
            patient.name = name
        if mobile:
            patient.mobile = mobile
        await db.commit()
        await db.refresh(patient)
        return patient

    patient = Patient(
        abha_id=patient_abha_id,
        name=name or f"Patient {patient_abha_id}",
        mobile=mobile,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def generate_link_token(patient_abha_id: str, hip_id: str, db: AsyncSession) -> Dict:
    """Generate a link token for a patient (auto-register if first seen)."""
    token = str(uuid.uuid4())
    txn_id = str(uuid.uuid4())

    await _ensure_patient(db, patient_abha_id)
    
    # Create a new linking request
    new_request = LinkingRequest(
        txn_id=txn_id,
        patient_abha_id=patient_abha_id,
        hip_id=hip_id,
        status="INITIATED",
        link_token=token
    )
    db.add(new_request)
    await db.commit()
    
    return {"token": token, "expiresIn": 300, "txnId": txn_id}


async def link_care_contexts(patient_abha_id: str, care_contexts: List[Dict], db: AsyncSession) -> Dict:
    """Link care contexts to a patient (auto-register if first seen)."""
    await _ensure_patient(db, patient_abha_id)
    created_count = 0
    
    for cc in care_contexts:
        existing = await db.execute(
            select(LinkedCareContext).where(
                LinkedCareContext.care_context_id == cc.get("id")
            )
        )
        if not existing.scalar():
            care_context = LinkedCareContext(
                patient_abha_id=patient_abha_id,
                care_context_id=cc.get("id"),
                reference_number=cc.get("referenceNumber"),
                hip_id=cc.get("hipId", "unknown")
            )
            db.add(care_context)
            created_count += 1
    
    await db.commit()
    return {"status": "LINKED", "count": created_count}


async def discover_patient(mobile: str, name: Optional[str], db: AsyncSession) -> Dict:
    """Discover a patient by mobile and name. Auto-register if not found."""
    result = await db.execute(select(Patient).where(Patient.mobile == mobile))
    patient = result.scalar_one_or_none()

    if patient:
        return {"patientId": patient.abha_id, "status": "FOUND"}

    generated_abha = f"pat-{mobile}"
    patient = await _ensure_patient(db, generated_abha, name=name, mobile=mobile)
    return {"patientId": patient.abha_id, "status": "REGISTERED"}


async def init_link(patient_abha_id: str, txn_id: str, db: AsyncSession) -> Dict:
        await _ensure_patient(db, patient_abha_id)
    """
    Initialize the linking process.
    Auto-approves linking requests (no OTP verification).
    """
    # Check if linking request exists
    result = await db.execute(
        select(LinkingRequest).where(LinkingRequest.txn_id == txn_id)
    )
    linking_request = result.scalar()
    
    if not linking_request:
        # Create new linking request with AUTO-APPROVED status
        linking_request = LinkingRequest(
            txn_id=txn_id,
            patient_abha_id=patient_abha_id,
            hip_id="unknown",
            status="LINKED"  # Auto-approve
        )
        db.add(linking_request)
        await db.commit()
    
    return {
        "status": "LINKED",
        "txnId": txn_id,
        "message": "Patient linking auto-approved"
    }


async def confirm_link(patient_abha_id: str, txn_id: str, otp: str, db: AsyncSession) -> Dict:
        await _ensure_patient(db, patient_abha_id)
    """
    Confirm the link with OTP.
    Auto-approves without OTP validation.
    """
    result = await db.execute(
        select(LinkingRequest).where(LinkingRequest.txn_id == txn_id)
    )
    linking_request = result.scalar()
    
    if not linking_request:
        # Create if doesn't exist (auto-approve)
        linking_request = LinkingRequest(
            txn_id=txn_id,
            patient_abha_id=patient_abha_id,
            hip_id="unknown",
            status="LINKED"
        )
        db.add(linking_request)
        await db.commit()
        return {
            "status": "CONFIRMED",
            "txnId": txn_id,
            "message": "Auto-approved (OTP not required)"
        }
    
    # Update status to LINKED (auto-approve)
    linking_request.status = "LINKED"
    await db.commit()
    
    return {
        "status": "CONFIRMED",
        "txnId": txn_id,
        "message": "Auto-approved (OTP not required)"
    }


async def notify_link(txn_id: str, status: str, db: AsyncSession) -> Dict:
    """Notify about linking status change."""
    result = await db.execute(
        select(LinkingRequest).where(LinkingRequest.txn_id == txn_id)
    )
    linking_request = result.scalar()
    
    if linking_request:
        linking_request.status = status
        await db.commit()
    
    return {"status": status, "txnId": txn_id}
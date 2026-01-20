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
    gender: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    aadhaar: Optional[str] = None,
) -> Patient:
    """Fetch or auto-register a patient by ABHA ID on first sight."""
    print(f"[DEBUG][gateway] _ensure_patient received gender: {gender}, date_of_birth: {date_of_birth}")
    result = await db.execute(select(Patient).where(Patient.abha_id == patient_abha_id))
    patient = result.scalar_one_or_none()

    if patient:
        # Update existing patient with new info if provided
        updated = False
        if name and patient.name != name:
            patient.name = name
            updated = True
        if mobile and patient.mobile != mobile:
            patient.mobile = mobile
            updated = True
        if gender and (not patient.gender or patient.gender != gender):
            patient.gender = gender
            updated = True
        if date_of_birth:
            from datetime import datetime
            try:
                dob_val = date_of_birth
                if isinstance(date_of_birth, str):
                    dob_val = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00'))
                if not patient.date_of_birth or patient.date_of_birth != dob_val:
                    patient.date_of_birth = dob_val
                    updated = True
            except:
                pass
        if updated:
            await db.commit()
            await db.refresh(patient)
            print(f"[DEBUG][gateway] Updated gender: {patient.gender}, date_of_birth: {patient.date_of_birth}")
        return patient

    # Create new patient with all provided data
    patient = Patient(
        abha_id=patient_abha_id,
        name=name or f"Patient {patient_abha_id}",
        mobile=mobile,
        gender=gender,
        date_of_birth=date_of_birth,
        abha_address=f"{(name or 'patient').lower().replace(' ', '.')}@sbx" if name else None,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    print(f"[DEBUG][gateway] Created gender: {patient.gender}, date_of_birth: {patient.date_of_birth}")
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


async def discover_patient(
    mobile: str,
    name: Optional[str],
    gender: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    aadhaar: Optional[str] = None,
    db: AsyncSession = None,
) -> Dict:
    """Discover a patient by mobile and name. Auto-register if not found."""
    try:
        print(f"[DEBUG][gateway] discover_patient received gender: {gender}, date_of_birth: {date_of_birth}")
        # First check if patient exists by mobile (most reliable identifier)
        result = await db.execute(select(Patient).where(Patient.mobile == mobile))
        patient = result.scalar_one_or_none()

        if patient:
            # Patient exists - update with any new demographic info
            updated = False
            if gender and not patient.gender:
                patient.gender = gender
                updated = True
            if date_of_birth and not patient.date_of_birth:
                # Parse date_of_birth if it's a string
                try:
                    from datetime import datetime
                    if isinstance(date_of_birth, str):
                        patient.date_of_birth = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00'))
                    else:
                        patient.date_of_birth = date_of_birth
                    updated = True
                except:
                    pass
            if name and patient.name != name:
                patient.name = name
                updated = True
            
            if updated:
                await db.commit()
                await db.refresh(patient)
            
            return {
                "patientId": patient.abha_id,
                "abhaId": patient.abha_id,
                "status": "FOUND",
                "gender": patient.gender if patient.gender is not None else "",
                "dateOfBirth": patient.date_of_birth.isoformat() if patient.date_of_birth else "",
                "abhaAddress": patient.abha_address,
            }

        # Patient not found by mobile - create new one
        import uuid
        generated_abha_id = f"abha-{str(uuid.uuid4())[:8]}"
        abha_address = f"{name.lower().replace(' ', '.')}@abdm" if name else f"pat-{mobile}@abdm"

        # Parse date_of_birth if it's a string
        parsed_dob = None
        if date_of_birth:
            try:
                from datetime import datetime
                if isinstance(date_of_birth, str):
                    parsed_dob = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00'))
                else:
                    parsed_dob = date_of_birth
            except:
                pass

        # Create new patient
        patient = Patient(
            abha_id=generated_abha_id,
            name=name or f"Patient {generated_abha_id}",
            mobile=mobile,
            gender=gender,
            date_of_birth=parsed_dob,
            abha_address=abha_address,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        return {
            "patientId": patient.abha_id,
            "abhaId": patient.abha_id,
            "status": "REGISTERED",
            "gender": patient.gender if patient.gender is not None else "",
            "dateOfBirth": patient.date_of_birth.isoformat() if patient.date_of_birth else "",
            "abhaAddress": patient.abha_address,
        }
    except Exception as e:
        return {"error": f"Failed to discover or register patient: {str(e)}"}


async def init_link(patient_abha_id: str, txn_id: str, hip_id: str = "HOSPITAL-1", db: AsyncSession = None) -> Dict:
    """
    Initialize the linking process.
    Auto-approves linking requests (no OTP verification).
    """
    # Fetch patient to get mobile number
    patient = await _ensure_patient(db, patient_abha_id)
    
    # Generate link token
    link_token = str(uuid.uuid4())
    
    result = await db.execute(
        select(LinkingRequest).where(LinkingRequest.txn_id == txn_id)
    )
    linking_request = result.scalar_one_or_none()

    if linking_request:
        linking_request.patient_abha_id = patient_abha_id
        linking_request.hip_id = hip_id
        linking_request.mobile = patient.mobile
        linking_request.link_token = link_token
        linking_request.status = "LINKED"
        await db.commit()
        await db.refresh(linking_request)
    else:
        linking_request = LinkingRequest(
            txn_id=txn_id,
            patient_abha_id=patient_abha_id,
            hip_id=hip_id,
            mobile=patient.mobile,
            link_token=link_token,
            status="LINKED"
        )
        db.add(linking_request)
        await db.commit()
        await db.refresh(linking_request)

    return {
        "status": "LINKED",
        "txnId": txn_id,
        "token": link_token,
        "message": "Patient linking auto-approved"
    }


async def confirm_link(patient_abha_id: str, txn_id: str, otp: str, hip_id: str = "HOSPITAL-1", db: AsyncSession = None) -> Dict:
    """
    Confirm the link with OTP.
    Auto-approves without OTP validation.
    """
    # Fetch patient to get mobile
    patient = await _ensure_patient(db, patient_abha_id)
    
    result = await db.execute(
        select(LinkingRequest).where(LinkingRequest.txn_id == txn_id)
    )
    linking_request = result.scalar_one_or_none()

    if not linking_request:
        linking_request = LinkingRequest(
            txn_id=txn_id,
            patient_abha_id=patient_abha_id,
            hip_id=hip_id,
            mobile=patient.mobile,
            status="CONFIRMED"
        )
        db.add(linking_request)
        await db.commit()
        await db.refresh(linking_request)
    else:
        linking_request.patient_abha_id = patient_abha_id
        linking_request.hip_id = hip_id
        linking_request.mobile = patient.mobile
        linking_request.status = "CONFIRMED"
        await db.commit()
        await db.refresh(linking_request)
    
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
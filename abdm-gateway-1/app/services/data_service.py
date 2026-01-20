import uuid
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import DataTransfer, ConsentRequest, Patient
from app.utils.encryption import encryptor
from app.services.task_processor import task_processor
from loguru import logger


async def _ensure_patient(db: AsyncSession, patient_abha_id: str) -> Patient:
    """Guarantee a patient exists to satisfy FK constraints."""
    result = await db.execute(select(Patient).where(Patient.abha_id == patient_abha_id))
    patient = result.scalar_one_or_none()
    if patient:
        return patient

    patient = Patient(abha_id=patient_abha_id, name=f"Patient {patient_abha_id}")
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def _ensure_consent_approved(
    db: AsyncSession,
    consent_id: Optional[str],
    patient_abha_id: str,
    hip_id: str
) -> str:
    """Ensure there is an approved consent; auto-approve if missing."""
    if consent_id:
        consent_result = await db.execute(
            select(ConsentRequest).where(ConsentRequest.consent_request_id == consent_id)
        )
        consent = consent_result.scalar_one_or_none()
        if consent:
            if consent.status != "APPROVED":
                consent.status = "APPROVED"
                await db.commit()
                await db.refresh(consent)
            return consent.consent_request_id

    # Create a fresh auto-approved consent when none is provided/found
    new_consent_id = consent_id or f"consent-{uuid.uuid4()}"
    consent = ConsentRequest(
        consent_request_id=new_consent_id,
        patient_abha_id=patient_abha_id,
        hip_id=hip_id,
        purpose={"text": "Auto-approved for data transfer"},
        status="APPROVED",
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return consent.consent_request_id


async def request_health_info(
    patient_abha_id: str,
    hip_id: str,
    hiu_id: str,
    consent_id: Optional[str],
    care_context_ids: List[str],
    data_types: List[str],
    db: AsyncSession,
) -> Dict:
    """HIU requests health information from HIP via Gateway."""
    await _ensure_patient(db, patient_abha_id)
    approved_consent_id = await _ensure_consent_approved(db, consent_id, patient_abha_id, hip_id)

    request_id = f"req-{uuid.uuid4()}"

    new_transfer = DataTransfer(
        transfer_id=request_id,
        consent_request_id=approved_consent_id,
        patient_abha_id=patient_abha_id,
        from_entity=hip_id,
        to_entity=hiu_id or "unknown-hiu",
        status="REQUESTED",
        data_count=len(data_types or []),
        next_retry_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(new_transfer)
    await db.commit()
    await db.refresh(new_transfer)

    logger.info(f"Created data request {request_id} from HIU {hiu_id} to HIP {hip_id}")

    webhook_sent = await task_processor.send_hip_data_request(
        db=db,
        transfer_id=request_id,
        hip_id=hip_id,
        hiu_id=hiu_id,
        patient_id=patient_abha_id,
        consent_id=approved_consent_id,
        care_context_ids=care_context_ids,
        data_types=data_types,
    )

    if webhook_sent:
        new_transfer.status = "FORWARDED"
    else:
        new_transfer.status = "FAILED"
        logger.error(f"Failed to forward request {request_id} to HIP {hip_id}")

    await db.commit()

    return {
        "requestId": request_id,
        "consentId": approved_consent_id,
        "status": new_transfer.status,
        "message": "Data request created and forwarded to HIP",
    }


async def receive_health_data_from_hip(
    request_id: str,
    health_data: Dict,
    db: AsyncSession
) -> Dict:
    """
    Receive health data from HIP and prepare for HIU delivery.
    
    This is called by HIP after it prepares the data.
    
    Args:
        request_id: Original request ID
        health_data: Health data bundle from HIP
        db: Database session
        
    Returns:
        Status of data receipt
    """
    # Find transfer request
    stmt = select(DataTransfer).where(DataTransfer.transfer_id == request_id)
    result = await db.execute(stmt)
    transfer = result.scalar_one_or_none()
    
    if not transfer:
        return {"error": "Request not found", "status": "FAILED"}
    
    if transfer.status not in ["REQUESTED", "FORWARDED", "PROCESSING"]:
        return {"error": f"Invalid request status: {transfer.status}", "status": "FAILED"}
    
    # Encrypt and store health data temporarily
    encrypted_data = encryptor.encrypt_dict(health_data)
    
    transfer.encrypted_data = encrypted_data
    transfer.status = "READY"
    transfer.next_retry_at = datetime.utcnow()  # Trigger immediate webhook delivery
    
    await db.commit()
    
    logger.info(f"Received health data for request {request_id}, ready for delivery")
    
    # Trigger immediate webhook delivery (will be picked up by background processor)
    
    return {
        "requestId": request_id,
        "status": "READY",
        "message": "Health data received and ready for delivery"
    }


async def send_health_info(
    txn_id: str,
    patient_id: str,
    hip_id: str,
    care_context_id: str,
    health_info: Dict,
    metadata: Dict,
    db: AsyncSession
) -> Dict:
    """
    Legacy method - Record sent health information.
    Kept for backward compatibility.
    """
    transfer_id = str(uuid.uuid4())
    
    new_transfer = DataTransfer(
        transfer_id=transfer_id,
        consent_request_id=txn_id,
        patient_abha_id=patient_id,
        from_entity=hip_id,
        to_entity="HIU",
        status="DELIVERED",
        data_count=1
    )
    db.add(new_transfer)
    await db.commit()
    
    return {"status": "RECEIVED", "txnId": txn_id}


async def get_data_request_status(request_id: str, db: AsyncSession) -> Optional[Dict]:
    """
    Get detailed status of a data request.
    
    Args:
        request_id: Request identifier
        db: Database session
        
    Returns:
        Detailed status information
    """
    result = await db.execute(
        select(DataTransfer).where(DataTransfer.transfer_id == request_id)
    )
    transfer = result.scalar()
    
    if transfer:
        status_info = {
            "requestId": request_id,
            "status": transfer.status,
            "patientId": transfer.patient_abha_id,
            "fromEntity": transfer.from_entity,
            "toEntity": transfer.to_entity,
            "dataCount": transfer.data_count,
            "createdAt": transfer.created_at.isoformat() if transfer.created_at else None,
            "updatedAt": transfer.updated_at.isoformat() if transfer.updated_at else None
        }
        
        # Add retry information if applicable
        if transfer.status in ["READY", "FAILED"]:
            status_info.update({
                "retryCount": transfer.retry_count,
                "maxRetries": transfer.max_retries,
                "webhookAttempts": transfer.webhook_attempts,
                "lastError": transfer.last_webhook_error
            })
        
        # Add expiration info if data is stored
        if transfer.encrypted_data:
            status_info["expiresAt"] = transfer.expires_at.isoformat() if transfer.expires_at else None
            status_info["dataStored"] = True
        else:
            status_info["dataStored"] = False
        
        return status_info
    
    return None


async def notify_data_flow(txn_id: str, status: str, hip_id: str, db: AsyncSession) -> Dict:
    """
    Notify about data flow status change.
    Legacy method for backward compatibility.
    """
    result = await db.execute(
        select(DataTransfer).where(DataTransfer.transfer_id == txn_id)
    )
    transfer = result.scalar()
    
    if transfer:
        transfer.status = status
        await db.commit()
        return {"status": status, "txnId": txn_id}
    
    return {"status": "NOT_FOUND", "txnId": txn_id}

import uuid
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import DataTransfer, ConsentRequest, Bridge
from app.utils.encryption import encryptor
from app.services.task_processor import task_processor
from loguru import logger


async def request_health_info(
    patient_id: str,
    hip_id: str,
    hiu_id: str,
    consent_id: str,
    care_context_ids: List[str],
    data_types: List[str],
    db: AsyncSession
) -> Dict:
    """
    HIU requests health information from HIP via Gateway.
    
    Flow:
    1. HIU calls this endpoint
    2. Gateway validates consent
    3. Gateway creates request record
    4. Gateway sends webhook to HIP
    5. HIP prepares data and responds
    6. Gateway stores encrypted data
    7. Gateway delivers to HIU via webhook
    
    Args:
        patient_id: Patient identifier
        hip_id: HIP bridge ID
        hiu_id: HIU bridge ID
        consent_id: Approved consent ID
        care_context_ids: List of care context IDs
        data_types: List of data types to fetch
        db: Database session
        
    Returns:
        Request status with requestId
    """
    # Validate consent
    consent_stmt = select(ConsentRequest).where(
        ConsentRequest.consent_request_id == consent_id
    )
    consent_result = await db.execute(consent_stmt)
    consent = consent_result.scalar_one_or_none()
    
    if not consent:
        return {"error": "Consent not found", "status": "FAILED"}
    
    if consent.status != "APPROVED":
        return {"error": f"Consent not approved. Current status: {consent.status}", "status": "FAILED"}
    
    # Create data transfer request
    request_id = f"req-{uuid.uuid4()}"
    
    new_transfer = DataTransfer(
        transfer_id=request_id,
        consent_request_id=consent_id,
        patient_id=patient_id,
        from_entity=hip_id,
        to_entity=hiu_id,
        status="REQUESTED",
        data_count=len(data_types),
        expires_at=datetime.utcnow() + timedelta(hours=24)  # Data expires in 24 hours
    )
    db.add(new_transfer)
    await db.commit()
    await db.refresh(new_transfer)
    
    logger.info(f"Created data request {request_id} from HIU {hiu_id} to HIP {hip_id}")
    
    # Send webhook to HIP (background task)
    webhook_sent = await task_processor.send_hip_data_request(
        db=db,
        transfer_id=request_id,
        hip_id=hip_id,
        patient_id=patient_id,
        consent_id=consent_id,
        care_context_ids=care_context_ids,
        data_types=data_types
    )
    
    if webhook_sent:
        # Update status to FORWARDED
        new_transfer.status = "FORWARDED"
        await db.commit()
        logger.info(f"Request {request_id} forwarded to HIP {hip_id}")
    else:
        logger.error(f"Failed to forward request {request_id} to HIP {hip_id}")
    
    return {
        "requestId": request_id,
        "status": new_transfer.status,
        "message": "Data request created and forwarded to HIP"
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
        patient_id=patient_id,
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
            "patientId": transfer.patient_id,
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

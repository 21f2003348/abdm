from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime
from app.deps.headers import require_gateway_headers
from app.deps.auth import get_current_token
from app.database.connection import get_db
from app.database.models import DataTransfer
from app.services.data_service import request_health_info, receive_health_data_from_hip
from sqlalchemy.future import select
from sqlalchemy import or_
from loguru import logger

router = APIRouter(prefix="/communication", tags=["hospital-communication"])


class DataRequestFromHIU(BaseModel):
    """Schema for HIU requesting data through gateway"""
    hiuId: str
    hipId: str
    patientId: str
    consentId: str
    careContextIds: List[str]
    dataTypes: List[str]


class DataResponseFromHIP(BaseModel):
    """Schema for HIP sending data back to gateway"""
    requestId: str
    patientId: str
    records: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


@router.post("/data-request")
async def request_patient_data(
    body: DataRequestFromHIU,
    background_tasks: BackgroundTasks,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    HIU requests patient data from HIP via Gateway.
    
    Flow:
    1. HIU calls this endpoint
    2. Gateway validates consent
    3. Gateway creates request record
    4. Gateway sends webhook to HIP
    5. Returns requestId to HIU for status tracking
    """
    logger.info(f"Data request from HIU {body.hiuId} for patient {body.patientId}")
    
    # Use the refactored data service
    result = await request_health_info(
        patient_id=body.patientId,
        hip_id=body.hipId,
        hiu_id=body.hiuId,
        consent_id=body.consentId,
        care_context_ids=body.careContextIds,
        data_types=body.dataTypes,
        db=db
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "status": "SUCCESS",
        "requestId": result["requestId"],
        "message": "Data request forwarded to HIP. Check status using /api/data/request/{requestId}/status"
    }


@router.post("/data-response")
async def receive_data_from_hip_endpoint(
    body: DataResponseFromHIP,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    HIP sends patient data back to Gateway.
    
    Flow:
    1. HIP calls this endpoint with data
    2. Gateway encrypts and stores data temporarily
    3. Gateway triggers delivery to HIU webhook
    4. Background task handles retry logic
    """
    logger.info(f"Data response received from HIP for request {body.requestId}")
    
    health_data = {
        "patientId": body.patientId,
        "records": body.records,
        "metadata": body.metadata,
        "receivedAt": datetime.utcnow().isoformat()
    }
    
    result = await receive_health_data_from_hip(
        request_id=body.requestId,
        health_data=health_data,
        db=db
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "status": "SUCCESS",
        "requestId": body.requestId,
        "message": "Data received and queued for delivery to HIU"
    }


@router.get("/messages/{bridge_id}")
async def get_bridge_messages(
    bridge_id: str,
    token=Depends(get_current_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all data transfer history for a specific bridge (HIP or HIU).
    """
    # Get data transfers where bridge is involved
    transfers_result = await db.execute(
        select(DataTransfer).where(
            or_(
                DataTransfer.from_entity == bridge_id,
                DataTransfer.to_entity == bridge_id
            )
        ).order_by(DataTransfer.created_at.desc())
    )
    transfers = transfers_result.scalars().all()
    
    return {
        "bridgeId": bridge_id,
        "count": len(transfers),
        "transfers": [
            {
                "transferId": t.transfer_id,
                "patientId": t.patient_id,
                "consentId": t.consent_request_id,
                "fromEntity": t.from_entity,
                "toEntity": t.to_entity,
                "status": t.status,
                "dataCount": t.data_count,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
                "updatedAt": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in transfers
        ]
    }

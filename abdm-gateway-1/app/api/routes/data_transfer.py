from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from app.deps.headers import require_gateway_headers
from app.deps.auth import get_current_token
from app.api.schemas import (
    SendHealthInfoRequest, SendHealthInfoResponse,
    RequestHealthInfoRequest, RequestHealthInfoResponse,
    DataFlowNotifyRequest, DataFlowNotifyResponse,
)
from app.services.data_service import (
    send_health_info, request_health_info,
    get_data_request_status, notify_data_flow,
    receive_health_data_from_hip
)
from app.database.connection import get_db

router = APIRouter(prefix="/data", tags=["data-transfer"])


# New schemas for refactored flow
class DataRequestCreate(BaseModel):
    """Schema for creating a data request (HIU → Gateway)"""
    patientId: str
    hipId: str
    hiuId: str
    consentId: str
    careContextIds: List[str]
    dataTypes: List[str]


class HIPDataResponse(BaseModel):
    """Schema for HIP responding with data (HIP → Gateway)"""
    requestId: str
    patientId: str
    records: List[dict]
    metadata: dict = {}


# New endpoints for refactored flow
@router.post("/request", response_model=dict)
async def create_data_request(
    body: DataRequestCreate,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    HIU creates a data request.
    Gateway validates consent and forwards to HIP.
    """
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
    
    return result


@router.post("/response", response_model=dict)
async def receive_data_from_hip(
    body: HIPDataResponse,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    HIP sends data response to Gateway.
    Gateway stores encrypted data and triggers delivery to HIU.
    """
    health_data = {
        "patientId": body.patientId,
        "records": body.records,
        "metadata": body.metadata
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
    
    return result


@router.get("/request/{request_id}/status")
async def get_request_status_endpoint(
    request_id: str = Path(...),
    token = Depends(get_current_token),
    headers = Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed status of a data request.
    HIU can poll this to check request progress.
    """
    request_status = await get_data_request_status(request_id, db)
    if not request_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    return request_status


# Legacy endpoints (kept for backward compatibility)
@router.post("/health-info", response_model=SendHealthInfoResponse)
async def send_health_info_endpoint(
    body: SendHealthInfoRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return SendHealthInfoResponse(
        **(await send_health_info(
            body.txnId, body.patientId, body.hipId,
            body.careContextId, body.healthInfo.dict(),
            body.metadata.dict(), db
        ))
    )


@router.post("/request-info", response_model=RequestHealthInfoResponse)
async def request_health_info_endpoint(
    body: RequestHealthInfoRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return RequestHealthInfoResponse(
        **(await request_health_info(
            body.patientId, body.hipId,
            body.careContextId, body.dataTypes, db
        ))
    )

@router.post("/notify", response_model=DataFlowNotifyResponse)
async def data_flow_notify_endpoint(
    body: DataFlowNotifyRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return DataFlowNotifyResponse(
        **(await notify_data_flow(body.txnId, body.status, body.hipId, db))
    )
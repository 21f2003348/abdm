"""
Data Requests API Routes for ABDM Hospital.
Provides endpoints for HIU to request and track patient data from HIP.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.gateway_service import (
    request_patient_data,
    check_request_status,
    get_communication_history,
    TokenManager
)

router = APIRouter(prefix="/api/data-requests", tags=["data-requests"])


# ============================================================================
# Schemas
# ============================================================================

class DataRequestCreate(BaseModel):
    """Schema for creating a new data request (HIU role)"""
    patientId: str
    hipId: str
    consentId: str
    careContextIds: List[str]
    dataTypes: List[str]


class DataRequestResponse(BaseModel):
    """Response when data request is created"""
    status: str
    requestId: str
    message: str
    hipId: str
    hiuId: str
    patientId: str
    createdAt: str


class DataRequestStatus(BaseModel):
    """Status of a data request"""
    requestId: str
    status: str
    patientId: str
    hipId: str
    hiuId: str
    dataCount: Optional[int] = None
    dataStored: bool = False
    retryCount: int = 0
    webhookAttempts: int = 0
    nextRetryAt: Optional[str] = None
    expiresAt: Optional[str] = None
    lastError: Optional[str] = None
    createdAt: str
    updatedAt: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=DataRequestResponse)
async def create_data_request(request: DataRequestCreate):
    """
    HIU: Request patient data from HIP via gateway.
    
    This initiates the flow:
    1. HIU calls this endpoint
    2. Gateway validates consent
    3. Gateway forwards request to HIP
    4. HIP fetches data and sends to gateway
    5. Gateway encrypts and queues delivery to HIU
    6. HIU receives data via webhook
    
    Body:
    - patientId: Patient identifier
    - hipId: HIP bridge ID to request data from
    - consentId: Approved consent request ID
    - careContextIds: List of care contexts to fetch
    - dataTypes: Types of data to request (PRESCRIPTION, DIAGNOSTIC_REPORT, etc.)
    
    Returns:
    - Request ID for tracking
    - Status and message
    """
    try:
        # Get HIU bridge ID from environment
        hiu_id = TokenManager.get_bridge_id_for_role("HIU")
        
        # Make request to gateway
        response = await request_patient_data(
            patient_id=request.patientId,
            hip_id=request.hipId,
            hiu_id=hiu_id,
            consent_id=request.consentId,
            care_context_ids=request.careContextIds,
            data_types=request.dataTypes
        )
        
        if "error" in response or response.get("status") != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=response.get("error") or response.get("message", "Request failed")
            )
        
        return DataRequestResponse(
            status=response.get("status"),
            requestId=response.get("requestId"),
            message=response.get("message"),
            hipId=request.hipId,
            hiuId=hiu_id,
            patientId=request.patientId,
            createdAt=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create data request: {str(e)}"
        )


@router.get("/{request_id}/status", response_model=DataRequestStatus)
async def get_request_status(request_id: str):
    """
    Check the status of a data request.
    
    Path Parameters:
    - request_id: Request identifier returned when creating request
    
    Returns:
    - Detailed status information including:
      - Current status (REQUESTED, FORWARDED, PROCESSING, READY, DELIVERED, FAILED)
      - Data availability
      - Retry information
      - Expiration timestamp
    """
    try:
        status_response = await check_request_status(request_id)
        
        if "error" in status_response:
            raise HTTPException(
                status_code=404,
                detail=status_response.get("error", "Request not found")
            )
        
        return DataRequestStatus(
            requestId=status_response.get("requestId"),
            status=status_response.get("status"),
            patientId=status_response.get("patientId"),
            hipId=status_response.get("fromEntity"),
            hiuId=status_response.get("toEntity"),
            dataCount=status_response.get("dataCount"),
            dataStored=status_response.get("dataStored", False),
            retryCount=status_response.get("retryCount", 0),
            webhookAttempts=status_response.get("webhookAttempts", 0),
            nextRetryAt=status_response.get("nextRetryAt"),
            expiresAt=status_response.get("expiresAt"),
            lastError=status_response.get("lastError"),
            createdAt=status_response.get("createdAt"),
            updatedAt=status_response.get("updatedAt")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get request status: {str(e)}"
        )


@router.get("/")
async def list_data_requests(
    limit: int = 20,
    offset: int = 0
):
    """
    List all data requests initiated by this HIU.
    
    Query Parameters:
    - limit: Maximum number of requests to return (default: 20)
    - offset: Number of requests to skip (default: 0)
    
    Returns:
    - List of data requests with basic information
    """
    try:
        # Get HIU bridge ID
        hiu_id = TokenManager.get_bridge_id_for_role("HIU")
        
        # Get communication history from gateway
        history = await get_communication_history(hiu_id)
        
        transfers = history.get("transfers", [])
        
        # Apply pagination
        paginated_transfers = transfers[offset:offset + limit]
        
        return {
            "total": len(transfers),
            "limit": limit,
            "offset": offset,
            "requests": [
                {
                    "requestId": t.get("transferId"),
                    "patientId": t.get("patientId"),
                    "status": t.get("status"),
                    "fromEntity": t.get("fromEntity"),
                    "toEntity": t.get("toEntity"),
                    "dataCount": t.get("dataCount"),
                    "createdAt": t.get("createdAt"),
                    "updatedAt": t.get("updatedAt")
                }
                for t in paginated_transfers
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list data requests: {str(e)}"
        )


@router.get("/history/{bridge_id}")
async def get_bridge_communication_history(bridge_id: str):
    """
    Get communication history for a specific bridge (HIP or HIU).
    
    Path Parameters:
    - bridge_id: Bridge identifier (hip-001, hiu-001, etc.)
    
    Returns:
    - List of all transfers involving this bridge
    """
    try:
        history = await get_communication_history(bridge_id)
        return history
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get communication history: {str(e)}"
        )


@router.get("/statistics")
async def get_request_statistics():
    """
    Get statistics about data requests initiated by this HIU.
    
    Returns:
    - Total requests
    - Count by status
    - Success rate
    - Average delivery time
    """
    try:
        # Get HIU bridge ID
        hiu_id = TokenManager.get_bridge_id_for_role("HIU")
        
        # Get communication history
        history = await get_communication_history(hiu_id)
        transfers = history.get("transfers", [])
        
        # Calculate statistics
        total_requests = len(transfers)
        status_counts = {}
        
        for transfer in transfers:
            status = transfer.get("status")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        delivered_count = status_counts.get("DELIVERED", 0)
        success_rate = (delivered_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "totalRequests": total_requests,
            "byStatus": status_counts,
            "successRate": round(success_rate, 2),
            "delivered": delivered_count,
            "failed": status_counts.get("FAILED", 0),
            "pending": status_counts.get("READY", 0) + status_counts.get("FORWARDED", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )

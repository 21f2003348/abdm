"""
Consent Management API Routes for ABDM Hospital.
Provides endpoints for initiating consent requests to fetch patient data.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.services.gateway_service import (
    init_consent_request,
    TokenManager
)

router = APIRouter(prefix="/api/consent", tags=["consent"])

class ConsentRequestCreate(BaseModel):
    """Schema for initiating a consent request"""
    patientId: str  # ABHA ID
    purpose: Optional[Dict[str, str]] = None
    hipId: Optional[str] = None
    hiuId: Optional[str] = None
    dataRange: Optional[Dict[str, str]] = None


class ConsentRequestResponse(BaseModel):
    """Response when consent request is initiated"""
    status: str
    consentRequestId: str
    message: str
    timestamp: str


@router.post("/init", response_model=ConsentRequestResponse)
async def initiate_consent_request(
    request: ConsentRequestCreate,
    background_tasks: BackgroundTasks
):
    """
    Initiate a consent request to the ABDM Gateway.
    
    This starts the flow:
    1. HIU calls this endpoint
    2. Hospital calls Gateway /api/consent/init
    3. Gateway notifies Patient App
    4. Patient approves consent
    5. Gateway notifies HIU (via Webhook)
    6. HIU requests data (handled by Webhook)
    
    Args:
        request: ConsentRequestCreate schema
        
    Returns:
        Consent Request ID and status
    """
    try:
        # Get hospital bridge ID for HIU role (for consent requests, we act as HIU)
        try:
            hiu_id = request.hiuId or TokenManager.get_bridge_id_for_role("HIU")
        except Exception:
            # Fallback to regular bridge ID if HIU role not configured
            hiu_id = TokenManager.get_bridge_details()[0]
        
        # Default purpose if not provided
        purpose = request.purpose or {
            "code": "CAREMGT",
            "text": "Care Management - Access to health records"
        }
        
        print(f"📝 Initiating consent request for patient: {request.patientId}")
        print(f"   Purpose: {purpose['text']}")
        print(f"   HIU ID: {hiu_id}")
        print(f"   HIP ID: {request.hipId or 'Any linked HIP'}")
        
        # Ensure we have a valid token before making the request
        try:
            token = TokenManager.get_token()
            if not token:
                print("⚠️  No access token found. Please authenticate with gateway first.")
        except Exception as e:
            print(f"⚠️  Token check warning: {str(e)}")
        
        # Call gateway service
        # Note: hip_id can be None - gateway will handle finding linked HIPs
        response = await init_consent_request(
            patient_id=request.patientId,
            hip_id=request.hipId,  # Can be None, Gateway handles it
            purpose=purpose
        )
        
        consent_request_id = response.get("consentRequestId")
        
        if not consent_request_id:
             raise HTTPException(
                status_code=500,
                detail=f"Gateway did not return a consent request ID: {response}"
            )
            
        print(f"✅ Consent request initiated: {consent_request_id}")
        
        return ConsentRequestResponse(
            status="INITIATED",
            consentRequestId=consent_request_id,
            message="Consent request sent to gateway. Waiting for patient approval.",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error initiating consent request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate consent request: {str(e)}"
        )

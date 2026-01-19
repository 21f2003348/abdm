from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.health_data_service import (
    get_mock_health_records,
    store_received_health_data,
    decrypt_and_store_health_data
)
from app.services.gateway_service import send_health_data_to_gateway, TokenManager

router = APIRouter(prefix="/webhook", tags=["webhook"])


# In-memory storage for received webhooks (for demo purposes)
webhook_queue: List[Dict[str, Any]] = []


class WebhookPayload(BaseModel):
    messageId: str
    messageType: str
    fromBridge: str
    timestamp: str
    payload: Dict[str, Any]


class DataRequestWebhook(BaseModel):
    requestId: str
    requestType: str
    patientId: str
    consentId: str
    careContextIds: List[str]
    dataTypes: List[str]
    hipId: str = None
    hiuId: str = None


class DataDeliveryWebhook(BaseModel):
    requestId: str
    status: str
    encryptedData: str
    dataCount: int
    expiresAt: str


@router.post("/receive")
async def receive_webhook(
    webhook: WebhookPayload,
    background_tasks: BackgroundTasks
):
    """
    Receive webhook notifications from the ABDM Gateway.
    This endpoint handles various message types sent by the gateway.
    """
    try:
        # Store webhook for processing
        webhook_data = {
            "receivedAt": datetime.utcnow().isoformat(),
            "messageId": webhook.messageId,
            "messageType": webhook.messageType,
            "fromBridge": webhook.fromBridge,
            "payload": webhook.payload
        }
        
        webhook_queue.append(webhook_data)
        
        # Log the webhook
        print(f"✓ Received webhook: {webhook.messageType} from {webhook.fromBridge}")
        print(f"  Message ID: {webhook.messageId}")
        print(f"  Payload: {json.dumps(webhook.payload, indent=2)}")
        
        # Process based on message type
        if webhook.messageType == "DATA_REQUEST":
            background_tasks.add_task(process_data_request, webhook.payload)
        elif webhook.messageType == "CONSENT_NOTIFICATION":
            background_tasks.add_task(process_consent_notification, webhook.payload)
        elif webhook.messageType == "LINK_NOTIFICATION":
            background_tasks.add_task(process_link_notification, webhook.payload)
        
        return {
            "status": "RECEIVED",
            "messageId": webhook.messageId,
            "message": "Webhook received and queued for processing"
        }
    except Exception as e:
        print(f"ERROR in /webhook/receive: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-request")
async def receive_data_request(
    request: DataRequestWebhook,
    background_tasks: BackgroundTasks
):
    """
    Specific endpoint for data requests from HIU via gateway.
    HIP uses this to receive data requests.
    
    Flow:
    1. Gateway sends request with patient/consent info
    2. HIP generates mock health records
    3. HIP sends response back to gateway via send_health_data_to_gateway()
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 DATA REQUEST RECEIVED FROM GATEWAY")
        print(f"{'='*60}")
        print(f"Request ID: {request.requestId}")
        print(f"Patient ID: {request.patientId}")
        print(f"Consent ID: {request.consentId}")
        print(f"Care Contexts: {', '.join(request.careContextIds)}")
        print(f"Data Types: {', '.join(request.dataTypes)}")
        print(f"From HIU: {request.hiuId}")
        print(f"To HIP: {request.hipId}")
        print(f"{'='*60}\n")
        
        # Store the request
        webhook_queue.append({
            "type": "DATA_REQUEST",
            "receivedAt": datetime.utcnow().isoformat(),
            "data": request.dict()
        })
        
        # Trigger background task to fetch and send health data
        background_tasks.add_task(
            fetch_and_send_health_data_to_gateway,
            request.requestId,
            request.patientId,
            request.careContextIds,
            request.dataTypes
        )
        
        return {
            "status": "ACCEPTED",
            "requestId": request.requestId,
            "message": "Data request accepted. Health data will be fetched and sent to gateway."
        }
    except Exception as e:
        print(f"ERROR in /webhook/data-request: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_webhook_queue():
    """Get all received webhooks (for debugging/monitoring)."""
    return webhook_queue[-20:]  # Last 20 webhooks


@router.delete("/queue")
async def clear_webhook_queue():
    """Clear the webhook queue."""
    webhook_queue.clear()
    return {"status": "CLEARED", "message": "Webhook queue cleared"}


@router.post("/data-delivery")
async def receive_data_delivery(
    webhook: DataDeliveryWebhook,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive encrypted health data delivery from gateway.
    HIU uses this endpoint to receive data sent by HIP.
    
    Flow:
    1. Gateway sends encrypted health data
    2. Hospital decrypts it using shared JWT_SECRET
    3. Hospital stores decrypted records in HealthRecord table
    """
    try:
        print(f"\n{'='*60}")
        print(f"📬 DATA DELIVERY RECEIVED FROM GATEWAY")
        print(f"{'='*60}")
        print(f"Request ID: {webhook.requestId}")
        print(f"Status: {webhook.status}")
        print(f"Data Count: {webhook.dataCount}")
        print(f"Encrypted Data Length: {len(webhook.encryptedData)} chars")
        print(f"Expires At: {webhook.expiresAt}")
        print(f"{'='*60}\n")
        
        # Store webhook for tracking
        webhook_queue.append({
            "type": "DATA_DELIVERY",
            "receivedAt": datetime.utcnow().isoformat(),
            "requestId": webhook.requestId,
            "status": webhook.status,
            "dataCount": webhook.dataCount
        })
        
        # Trigger background task to decrypt and store data
        background_tasks.add_task(
            decrypt_and_store_webhook_data,
            webhook.requestId,
            webhook.encryptedData,
            db
        )
        
        return {
            "status": "RECEIVED",
            "requestId": webhook.requestId,
            "message": "Encrypted data received. Decryption and storage in progress."
        }
    except Exception as e:
        print(f"ERROR in /webhook/data-delivery: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Background processing functions
# ============================================================================

async def process_data_request(payload: Dict[str, Any]):
    """Process incoming data request."""
    request_id = payload.get('requestId', 'unknown')
    print(f"📥 Processing data request: {request_id}")
    print(f"   Patient: {payload.get('patientId')}")
    print(f"   Care Contexts: {payload.get('careContextIds', [])}")
    # Real implementation would:
    # 1. Validate consent
    # 2. Query hospital DB for patient records
    # 3. Call send_health_data_to_gateway()


async def process_consent_notification(payload: Dict[str, Any]):
    """Process consent status notification."""
    consent_id = payload.get('consentId', 'unknown')
    status = payload.get('status', 'UNKNOWN')
    print(f"📥 Processing consent notification: {consent_id}")
    print(f"   Status: {status}")
    # Real implementation would:
    # 1. Update local consent_requests table
    # 2. Notify relevant departments/users
    # 3. Trigger data preparation if approved


async def process_link_notification(payload: Dict[str, Any]):
    """Process linking notification."""
    txn_id = payload.get('txnId', 'unknown')
    status = payload.get('status', 'UNKNOWN')
    print(f"📥 Processing link notification: {txn_id}")
    print(f"   Status: {status}")
    # Real implementation would:
    # 1. Update local linking_requests table
    # 2. Activate care contexts if linked
    # 3. Notify patient registration system


async def fetch_and_send_health_data_to_gateway(
    request_id: str,
    patient_id: str,
    care_context_ids: List[str],
    data_types: List[str]
):
    """
    HIP: Fetch health data from database and send to gateway.
    
    This simulates the HIP preparing and sending patient data back through the gateway.
    
    Args:
        request_id: Request ID from the data request
        patient_id: Patient identifier
        care_context_ids: Care contexts to fetch for
        data_types: Types of data to fetch
    """
    try:
        print(f"\n🔍 HIP: Fetching health data for request {request_id}...")
        
        # Get mock health records (in production, this would query the actual hospital DB)
        records = await get_mock_health_records(
            patient_id=patient_id,
            data_types=data_types,
            care_context_ids=care_context_ids
        )
        
        print(f"✅ HIP: Fetched {len(records)} health records")
        
        # Send response to gateway
        print(f"📤 HIP: Sending health data to gateway...")
        response = await send_health_data_to_gateway(
            request_id=request_id,
            patient_id=patient_id,
            records=records,
            metadata={"sourceHospital": TokenManager.get_bridge_id_for_role("HIP")}
        )
        
        print(f"✅ HIP: Gateway response: {response}")
        
    except Exception as e:
        print(f"❌ HIP: Error fetching/sending health data: {str(e)}")


async def decrypt_and_store_webhook_data(
    request_id: str,
    encrypted_data: str,
    db: Session
):
    """
    HIU: Decrypt encrypted data and store it in the database.
    
    Args:
        request_id: Request ID for tracking
        encrypted_data: Encrypted health data from gateway
        db: Database session
    """
    try:
        print(f"\n🔐 HIU: Decrypting health data for request {request_id}...")
        
        # Extract patient_id from request (in real system, would look up in request tracking)
        # For now, use a default patient ID
        patient_id = "patient-001"
        
        # Decrypt and store
        success = await decrypt_and_store_health_data(
            db=db,
            patient_id=patient_id,
            encrypted_data=encrypted_data,
            source_hospital="hip-001",
            request_id=request_id
        )
        
        if success:
            print(f"✅ HIU: Successfully decrypted and stored health data for request {request_id}")
        else:
            print(f"❌ HIU: Failed to decrypt or store health data for request {request_id}")
            
    except Exception as e:
        print(f"❌ HIU: Error in decrypt_and_store_webhook_data: {str(e)}")

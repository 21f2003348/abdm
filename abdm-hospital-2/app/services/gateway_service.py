import httpx
from fastapi import HTTPException
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv, set_key
import os
import requests
from typing import Dict, Any, List

load_dotenv()

def get_gateway_base_url():
    """Get gateway URL from environment, default to localhost:8000"""
    return os.getenv("GATEWAY_BASE_URL", "http://localhost:8000")

GATEWAY_BASE_URL = get_gateway_base_url()

class TokenManager:
    @classmethod
    def refresh_token(cls):
        """Force refresh the token by calling the authentication endpoint."""
        client_id, client_secret = cls.get_client_credentials()
        response = requests.post(
            f"{GATEWAY_BASE_URL}/api/auth/session",
            json={"clientId": client_id, "clientSecret": client_secret, "grantType": "client_credentials"},
            headers=headers1,
        )
        if response.status_code == 200:
            new_token = response.json()["accessToken"]
            cls.set_token(new_token)
            return new_token
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to refresh token.")

    @classmethod
    def get_token(cls):
        token = os.getenv("ACCESS_TOKEN")
        if not token:
            return cls.refresh_token()  # Refresh token if not available
        return token

    @classmethod
    def set_token(cls, token):
        set_key(".env", "ACCESS_TOKEN", token)

    @classmethod
    def get_client_credentials(cls):
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(status_code=401, detail="Client credentials not available. Please set them in the .env file.")
        return client_id, client_secret

    @classmethod
    def get_bridge_details(cls):
        bridge_id = os.getenv("BRIDGE_ID_HIP") or os.getenv("BRIDGE_ID")
        entity_type = os.getenv("ENTITY_TYPE")
        name = os.getenv("NAME")
        webhook = os.getenv("WEBHOOK_URL")
        if not bridge_id or not entity_type or not name or not webhook:
            raise HTTPException(status_code=401, detail="Bridge details not available. Please set them in the .env file.")
        return bridge_id, entity_type, name, webhook
    
    @classmethod
    def get_webhook_details(cls):
        webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("HOSPITAL_WEBHOOK_URL")
        bridge_id = os.getenv("BRIDGE_ID_HIP") or os.getenv("BRIDGE_ID")
        if not webhook_url or not bridge_id:
            raise HTTPException(status_code=401, detail="Webhook details not available. Please set them in the .env file.")
        return webhook_url, bridge_id

    @classmethod
    def set_service_id(cls, service_id):
        set_key(".env", "SERVICE_ID", service_id)

    @classmethod
    def get_service_id(cls):
        service_id = os.getenv("SERVICE_ID")
        if not service_id:
            raise HTTPException(status_code=401, detail="Service ID not available. Please list services first.")
        return service_id
    
    @classmethod
    def get_link_token(cls):
        link_token = os.getenv("LINK_TOKEN")
        if not link_token:
            raise HTTPException(status_code=401, detail="Link token not available. Please generate it first.")
        return link_token

    @classmethod
    def set_link_token(cls, link_token):
        set_key(".env", "LINK_TOKEN", link_token)
    
    @classmethod
    def get_gateway_url(cls):
        """Get gateway URL from environment"""
        return get_gateway_base_url()
    
    @classmethod
    def get_jwt_secret(cls):
        """Get JWT secret for decryption"""
        return os.getenv("GATEWAY_JWT_SECRET", "dev-secret-123")
    
    @classmethod
    def get_x_cm_id(cls):
        """Get X-CM-ID header value"""
        return os.getenv("X_CM_ID", "hospital-main")
    
    @classmethod
    def get_bridge_id_for_role(cls, role: str):
        """Get bridge ID for specific role (HIP or HIU)"""
        return os.getenv(f"BRIDGE_ID_{role.upper()}", f"{role.lower()}-001")
    
    @classmethod
    def get_hospital_webhook_url(cls):
        """Get hospital's own webhook URL for receiving data"""
        return os.getenv("HOSPITAL_WEBHOOK_URL", "http://localhost:8080/webhook")


headers1 = {
    "REQUEST-ID": str(uuid.uuid4()),
    "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
    "X-CM-ID": os.getenv("X_CM_ID", "hospital-main")
}

def get_headers_with_auth():
    return {
        "REQUEST-ID": str(uuid.uuid4()),
        "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
        "X-CM-ID": os.getenv("X_CM_ID", "hospital-main"),
        "Authorization": f"Bearer {TokenManager.get_token()}",
        "Content-Type": "application/json"
    }

async def gateway_health_check():
    """Check the health of the ABDM Gateway."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GATEWAY_BASE_URL}/health")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Gateway unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=response.status_code, detail=f"Gateway error: {exc.response.text}")

async def create_auth_session():
    """Call the /api/auth/session endpoint to create an authentication session."""
    client_id, client_secret = TokenManager.get_client_credentials()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/auth/session",
            json={"clientId": client_id, "clientSecret": client_secret, "grantType": "client_credentials"},
            headers=headers1,
        )
        response_data = response.json()
        TokenManager.set_token(response_data["accessToken"])
        return response_data

# Bridge Management
async def register_bridge():
    """Call the /api/bridge/register endpoint to register a bridge."""
    bridge_id, entity_type, name, _ = TokenManager.get_bridge_details()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/bridge/register",
            json={"bridgeId": bridge_id, "entityType": entity_type, "name": name},
            headers=get_headers_with_auth(),
        )
        return response.json()
    
async def update_bridge_webhook():
    """Call the /api/bridge/update-webhook endpoint to update the bridge webhook."""
    webhook_url, bridge_id = TokenManager.get_webhook_details()
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{GATEWAY_BASE_URL}/api/bridge/url",
            json={"bridgeId": bridge_id, "webhookUrl": webhook_url},
            headers=get_headers_with_auth(),
        )
        return response.json()

async def list_services():
    """Call the /api/services/list endpoint to list services."""
    async with httpx.AsyncClient() as client:
        bridge_id, _, _, _ = TokenManager.get_bridge_details()
        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/bridge/{bridge_id}/services",
            headers=get_headers_with_auth(),
        )
        response_data = response.json()
        # Gateway returns a list; persist the first service id if available
        if isinstance(response_data, list) and response_data:
            TokenManager.set_service_id(response_data[0].get("id"))
        return response_data
    
async def get_service_details():
    """Call the /api/services/{serviceId} endpoint to get service details."""
    async with httpx.AsyncClient() as client:
        service_id = TokenManager.get_service_id()

        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/bridge/service/{service_id}",
            headers=get_headers_with_auth(),
        )
        return response.json()
    
# Linking 
async def generate_link_token(patient_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/link/token/generate",
            headers=get_headers_with_auth(),
            json={"hipId": TokenManager.get_bridge_details()[0], "patientId": patient_id}
        )
        TokenManager.set_link_token(response.json()["token"])
        print(response.json()["token"])
        return response.json()
       

async def link_care_contexts_to_gateway(payload: Dict[str, Any]):
    """Link care contexts using gateway schema."""
    body = {
        "patientId": payload.get("patientId"),
        "careContexts": [
            {
                "id": payload.get("careContextId") or cc.get("id"),
                "referenceNumber": payload.get("referenceNumber") or cc.get("referenceNumber"),
            }
            for cc in payload.get("careContexts", [{}])
            if cc.get("id") or payload.get("careContextId")
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/api/link/carecontext",
                headers=get_headers_with_auth(),
                json=body,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Check if it's a token expiration error
            if e.response.status_code == 401 or "expired token" in str(e.response.text).lower():
                # Try to refresh the token and retry once
                try:
                    TokenManager.refresh_token()
                    # Retry with new token
                    response = await client.post(
                        f"{GATEWAY_BASE_URL}/api/link/carecontext",
                        headers=get_headers_with_auth(),
                        json=body,
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as refresh_error:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Token expired and refresh failed: {str(refresh_error)}"
                    )
            raise

async def discover_patient(payload: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/link/discover",
            headers=get_headers_with_auth(),
            json=payload
        )
        return response.json()
    
async def init_link(payload: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/link/init",
            headers=get_headers_with_auth(),
            json=payload
        )
        return response.json()
    
async def confirm_link(payload: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/link/confirm",
            headers=get_headers_with_auth(),
            json=payload
        )
        return response.json()  

async def notify_linking(payload: Dict[str, Any]):
    """Notify gateway about linking status changes."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/link/notify",
            headers=get_headers_with_auth(),
            json=payload
        )
        response.raise_for_status()
        return response.json()

async def communicate_with_hospital(payload: Dict[str, Any], hospital_id: str):
    """
    Communicate with another hospital via the gateway.

    Args:
        payload (Dict[str, Any]): The data to send to the hospital.
        hospital_id (str): The ID of the hospital to communicate with.

    Returns:
        Dict[str, Any]: The response from the gateway.
    """
    bridge_id = TokenManager.get_bridge_details()[0]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/communication/send-message",
            json={
                "fromBridgeId": bridge_id,
                "toBridgeId": hospital_id,
                "messageType": "DATA_EXCHANGE",
                "payload": payload
            },
            headers=get_headers_with_auth()
        )
        return response.json()


async def request_patient_data(
    patient_id: str,
    hip_id: str,
    hiu_id: str,
    consent_id: str,
    care_context_ids: List[str],
    data_types: List[str]
):
    """
    Request patient data from HIP via Gateway (HIU role).
    
    New Flow:
    1. HIU calls Gateway's /api/communication/data-request
    2. Gateway validates consent
    3. Gateway forwards request to HIP webhook
    4. Gateway returns requestId for status tracking
    
    Args:
        patient_id: The patient's ID
        hip_id: HIP bridge ID
        hiu_id: HIU bridge ID (caller)
        consent_id: The approved consent request ID
        care_context_ids: List of care context IDs to fetch data for
        data_types: List of data types to fetch (e.g., ["PRESCRIPTION", "DIAGNOSTIC_REPORT"])
    
    Returns:
        Dict with request status and requestId
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/communication/data-request",
            json={
                "hiuId": hiu_id,
                "hipId": hip_id,
                "patientId": patient_id,
                "consentId": consent_id,
                "careContextIds": care_context_ids,
                "dataTypes": data_types
            },
            headers=get_headers_with_auth()
        )
        return response.json()


async def send_health_data_to_gateway(
    request_id: str,
    patient_id: str,
    records: List[dict],
    metadata: dict = None
):
    """
    Send health data response to Gateway (HIP role).
    
    New Flow:
    1. HIP receives data request via webhook
    2. HIP fetches patient records from database
    3. HIP calls Gateway's /api/communication/data-response
    4. Gateway encrypts and stores data temporarily
    5. Gateway triggers delivery to HIU via webhook
    
    Args:
        request_id: The original request ID from the data request webhook
        patient_id: The patient's ID
        records: List of health records
        metadata: Optional metadata
    
    Returns:
        Dict with response status
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_BASE_URL}/api/communication/data-response",
            json={
                "requestId": request_id,
                "patientId": patient_id,
                "records": records,
                "metadata": metadata or {}
            },
            headers=get_headers_with_auth()
        )
        return response.json()


async def check_request_status(request_id: str):
    """
    Check the status of a data request (HIU role).
    
    Args:
        request_id: Request identifier
        
    Returns:
        Detailed request status including retry info
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/data/request/{request_id}/status",
            headers=get_headers_with_auth()
        )
        return response.json()


async def get_communication_history(bridge_id: str):
    """
    Get communication history for a bridge (hospital).
    
    Args:
        bridge_id: The bridge ID to get history for
    
    Returns:
        Dict with list of messages/transfers
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GATEWAY_BASE_URL}/api/communication/messages/{bridge_id}",
            headers=get_headers_with_auth()
        )
        return response.json()


async def notify_gateway_new_record(payload: Dict[str, Any]):
    """
    Notify the ABDM Gateway about a newly created health record.
    This allows the gateway to index the record for potential sharing.
    
    Args:
        payload: Dict containing:
            - patientId: UUID of the patient
            - patientAbhaId: ABHA ID of the patient
            - recordId: UUID of the health record
            - recordType: Type of record (PRESCRIPTION, DIAGNOSTIC_REPORT, etc.)
            - recordDate: ISO date string
            - createdAt: ISO timestamp
            - title: Record title
    
    Returns:
        Gateway response
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/api/health-records/notify",
                headers=get_headers_with_auth(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # If endpoint doesn't exist yet, return success anyway
            if e.response.status_code == 404:
                return {
                    "status": "acknowledged",
                    "message": "Gateway endpoint not yet implemented, record saved locally"
                }
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to notify gateway: {str(e)}"
            )


async def main():
    # print(await create_auth_session())
    # print(await register_bridge())
    # print(await list_services())
    # print(await update_bridge_webhook())
    # print(await get_service_details())
    # print(await generate_link_token("patient-12345"))
    # payload = {
    #     "patientId": "patient-12345",
    #     "careContexts": [
    #         {
    #             "id": "cc-001",
    #             "referenceNumber": "OPD-2025-001"
    #         },
    #         {
    #             "id": "cc-002",
    #             "referenceNumber": "IPD-2025-005"
    #         }
    #     ]
    # }
    # print(await link_care_contexts_to_gateway(payload))
    payload = {
        "message": "Hello, this is a test message to another hospital."
    }
    hospital_id = "hospital-12345"
    print(await communicate_with_hospital(payload, hospital_id))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.gateway_service import (
    create_auth_session,
    register_bridge,
    generate_link_token,
    link_care_contexts_to_gateway,
    init_link,
    confirm_link,
    request_patient_data,
    send_health_data_to_gateway,
    get_communication_history,
    TokenManager
)
import uuid

router = APIRouter(prefix="/demo", tags=["demo-workflows"])


class PatientLinkingDemo(BaseModel):
    patientId: str
    mobile: str
    careContexts: List[Dict[str, str]]


class DataRequestDemo(BaseModel):
    patientId: str
    consentId: str
    careContextIds: List[str]
    dataTypes: List[str]


@router.post("/setup-bridge")
async def setup_bridge_demo():
    """
    Complete demo: Setup bridge with gateway.
    Step 1: Authenticate with gateway
    Step 2: Register this hospital as a bridge
    Step 3: Update webhook URL
    """
    results = {}
    
    try:
        # Step 1: Authenticate
        auth_response = await create_auth_session()
        results["authentication"] = {
            "status": "✓ SUCCESS",
            "tokenReceived": "accessToken" in auth_response
        }
        
        # Step 2: Register Bridge
        register_response = await register_bridge()
        results["registration"] = {
            "status": "✓ SUCCESS",
            "bridgeId": register_response.get("bridgeId"),
            "entityType": register_response.get("entityType")
        }
        
        return {
            "workflow": "Bridge Setup",
            "status": "COMPLETED",
            "steps": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.post("/link-patient")
async def link_patient_demo(request: PatientLinkingDemo):
    """
    Complete demo: Link patient to this hospital.
    Step 1: Generate link token
    Step 2: Link care contexts
    """
    results = {}
    
    try:
        # Step 1: Generate link token
        token_response = await generate_link_token(request.patientId)
        results["tokenGeneration"] = {
            "status": "✓ SUCCESS",
            "token": token_response.get("token"),
            "expiresIn": token_response.get("expiresIn")
        }
        
        # Step 2: Link care contexts
        link_payload = {
            "patientId": request.patientId,
            "careContexts": request.careContexts
        }
        link_response = await link_care_contexts_to_gateway(link_payload)
        results["linking"] = {
            "status": "✓ SUCCESS",
            "response": link_response
        }
        
        return {
            "workflow": "Patient Linking",
            "status": "COMPLETED",
            "patientId": request.patientId,
            "steps": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Linking failed: {str(e)}")


@router.post("/request-data")
async def request_data_demo(request: DataRequestDemo):
    """
    Complete demo: Request patient data from another hospital.
    This demonstrates HIU (Health Information User) requesting data from HIP.
    
    Prerequisites:
    - Patient must be linked to the HIP
    - Consent must be approved
    """
    try:
        # Request data through gateway
        response = await request_patient_data(
            patient_id=request.patientId,
            consent_id=request.consentId,
            care_context_ids=request.careContextIds,
            data_types=request.dataTypes
        )
        
        return {
            "workflow": "Data Request",
            "status": "COMPLETED",
            "requestDetails": {
                "patientId": request.patientId,
                "consentId": request.consentId,
                "careContexts": request.careContextIds,
                "dataTypes": request.dataTypes
            },
            "gatewayResponse": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data request failed: {str(e)}")


@router.post("/send-data")
async def send_data_demo(
    request_id: str,
    patient_id: str,
    consent_id: str
):
    """
    Complete demo: Send patient data to gateway.
    This demonstrates HIP responding to a data request.
    
    In real scenario, this would be triggered by receiving a webhook
    from the gateway with a data request.
    """
    try:
        # Simulate health data (in real system, fetch from database)
        health_data = {
            "patientId": patient_id,
            "records": [
                {
                    "type": "PRESCRIPTION",
                    "date": "2025-01-15",
                    "doctor": "Dr. Smith",
                    "medications": [
                        {"name": "Paracetamol", "dosage": "500mg", "frequency": "Twice daily"}
                    ]
                },
                {
                    "type": "DIAGNOSTIC_REPORT",
                    "date": "2025-01-14",
                    "test": "Blood Test",
                    "results": {"hemoglobin": "14.5 g/dL", "wbc": "7500 cells/μL"}
                }
            ]
        }
        
        response = await send_health_data_to_gateway(
            request_id=request_id,
            patient_id=patient_id,
            consent_id=consent_id,
            health_data=health_data
        )
        
        return {
            "workflow": "Data Push (HIP Response)",
            "status": "COMPLETED",
            "requestId": request_id,
            "recordsSent": len(health_data["records"]),
            "gatewayResponse": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data push failed: {str(e)}")


@router.get("/communication-history")
async def get_history_demo():
    """
    Get communication history for this hospital.
    Shows all data exchanges this hospital was involved in.
    """
    try:
        bridge_id = TokenManager.get_bridge_details()[0]
        history = await get_communication_history(bridge_id)
        
        return {
            "workflow": "Communication History",
            "bridgeId": bridge_id,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/complete-flow-guide")
async def get_complete_flow_guide():
    """
    Returns a guide showing the complete hospital-to-hospital communication flow.
    """
    return {
        "title": "Hospital-to-Hospital Communication Flow via ABDM Gateway",
        "flows": {
            "1. Setup": {
                "description": "Initial setup for hospitals",
                "steps": [
                    "POST /demo/setup-bridge - Authenticate and register with gateway",
                    "Set WEBHOOK_URL in .env to receive notifications"
                ]
            },
            "2. Patient Linking (by HIP)": {
                "description": "Hospital links patient records",
                "steps": [
                    "POST /demo/link-patient - Link patient with care contexts",
                    "Patient can now access records through ABDM"
                ]
            },
            "3. Consent Request (by HIU)": {
                "description": "Request consent to access patient data",
                "steps": [
                    "POST /api/consent/init - HIU requests consent",
                    "Patient approves consent (external system)",
                    "GET /api/consent/status/{id} - Check consent status"
                ]
            },
            "4. Data Request (by HIU)": {
                "description": "HIU requests patient data from HIP",
                "steps": [
                    "POST /demo/request-data - Request data with consent",
                    "Gateway validates consent and forwards to HIP",
                    "HIP receives webhook notification at /webhook/data-request"
                ]
            },
            "5. Data Response (by HIP)": {
                "description": "HIP sends data to gateway",
                "steps": [
                    "POST /demo/send-data - HIP pushes health data",
                    "Gateway logs transfer and forwards to HIU",
                    "HIU receives data via webhook"
                ]
            },
            "6. Monitor": {
                "description": "Track communication",
                "steps": [
                    "GET /demo/communication-history - View all exchanges",
                    "GET /webhook/queue - Check received webhooks"
                ]
            }
        },
        "roles": {
            "HIP": "Health Information Provider (Hospital with patient records)",
            "HIU": "Health Information User (Hospital/Insurance requesting data)",
            "Gateway": "ABDM Gateway (Mediates all communication)"
        }
    }

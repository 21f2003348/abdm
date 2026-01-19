from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.connection import get_db
from typing import Optional, Dict, Any
import uuid
from app.database.models import CareContext
from app.services.gateway_service import link_care_contexts_to_gateway, communicate_with_hospital

router = APIRouter()

# Models
class CareContextRequest(BaseModel):
    patientId: str
    contextName: str
    description: Optional[str] = None

class CareContextResponse(BaseModel):
    contextId: str
    patientId: str
    contextName: str
    description: Optional[str]

# Database Logic
def create_care_context(db: Session, context_data: CareContextRequest):
    """Insert a new care context into the database."""
    new_context = CareContext(
        patient_id=uuid.UUID(context_data.patientId),  # Convert to UUID
        context_name=context_data.contextName,
        description=context_data.description
    )
    db.add(new_context)
    db.commit()
    db.refresh(new_context)
    return {
        "contextId": str(new_context.id),  # Ensure UUID is converted to string
        "patientId": str(new_context.patient_id),  # Convert back to string for response
        "contextName": new_context.context_name,
        "description": new_context.description
    }

@router.post("/api/care-context/create-and-link")
async def create_and_link_care_context(
    request: CareContextRequest,
    db: Session = Depends(get_db)
):
    """Create a care context and immediately link it to the ABDM Gateway."""
    # Create the care context in the database
    new_context = create_care_context(db, request)

    # Prepare payload for the gateway
    payload = {
        "patientId": new_context["patientId"],
        "careContexts": [
            {
                "id": new_context["contextId"],
                "referenceNumber": new_context["contextName"]
            }
        ]
    }

    # Try to communicate with gateway, but don't fail if gateway is unavailable
    try:
        gateway_response = await link_care_contexts_to_gateway(payload)
        return {
            "localContext": new_context,
            "gatewayResponse": gateway_response
        }
    except Exception as e:
        # Log the error but still return the local context
        print(f"Warning: Failed to link care context to gateway: {str(e)}")
        return {
            "localContext": new_context,
            "gatewayResponse": {
                "status": "pending",
                "error": str(e),
                "message": "Care context created locally but gateway linking failed. This is normal if gateway is not running."
            }
        }

@router.get("/api/care-context/list")
async def list_care_contexts(db: Session = Depends(get_db)):
    """List all care contexts from the database."""
    contexts = db.query(CareContext).all()
    return [
        {
            "contextId": str(c.id),
            "patientId": str(c.patient_id),
            "contextName": c.context_name,
            "description": c.description
        }
        for c in contexts
    ]

@router.get("/api/care-contexts/{patient_id}")
async def get_care_contexts_by_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get all care contexts for a specific patient."""
    try:
        patient_uuid = uuid.UUID(patient_id)
        contexts = db.query(CareContext).filter(CareContext.patient_id == patient_uuid).all()
        return [
            {
                "contextId": str(c.id),
                "patientId": str(c.patient_id),
                "contextName": c.context_name,
                "description": c.description
            }
            for c in contexts
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hospital/communicate")
async def communicate_with_other_hospital(
    hospital_id: str,
    payload: Dict[str, Any]
):
    """Communicate with another hospital via the gateway."""
    response = await communicate_with_hospital(payload, hospital_id)
    return response
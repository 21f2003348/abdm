import uuid
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import ConsentRequest


async def init_consent(patient_id: str, hip_id: str, purpose: Dict, db: AsyncSession) -> Dict:
    """Initialize a consent request."""
    consent_id = str(uuid.uuid4())
    
    new_consent = ConsentRequest(
        consent_request_id=consent_id,
        patient_id=patient_id,
        hip_id=hip_id,
        purpose=purpose,
        status="INITIATED"
    )
    db.add(new_consent)
    await db.commit()
    
    return {"consentRequestId": consent_id, "status": "INITIATED"}


async def get_consent_status(consent_id: str, db: AsyncSession) -> Optional[Dict]:
    """Get the status of a consent request."""
    result = await db.execute(
        select(ConsentRequest).where(ConsentRequest.consent_request_id == consent_id)
    )
    consent = result.scalar()
    
    if consent:
        return {
            "consentRequestId": consent_id,
            "status": consent.status,
            "createdAt": consent.created_at.isoformat() if consent.created_at else None
        }
    return None


async def fetch_consent(consent_id: str, db: AsyncSession) -> Optional[Dict]:
    """Fetch a consent artefact."""
    result = await db.execute(
        select(ConsentRequest).where(ConsentRequest.consent_request_id == consent_id)
    )
    consent = result.scalar()
    
    if consent:
        return {
            "consentRequestId": consent_id,
            "status": consent.status,
            "consentArtefact": {"data": "encrypted-consent-artefact"}
        }
    return None


async def notify_consent(consent_id: str, status: str, db: AsyncSession) -> Dict:
    """Update consent status via notification."""
    result = await db.execute(
        select(ConsentRequest).where(ConsentRequest.consent_request_id == consent_id)
    )
    consent = result.scalar()
    
    if consent:
        consent.status = status
        await db.commit()
        return {"consentRequestId": consent_id, "status": status}
    
    return {"consentRequestId": consent_id, "status": "NOT_FOUND"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.headers import require_gateway_headers
from app.deps.auth import get_current_token
from app.api.schemas import (
    ConsentInitRequest, ConsentInitResponse,
    ConsentStatusResponse,
    ConsentFetchRequest, ConsentFetchResponse,
    ConsentNotifyRequest
)
from app.services.consent_service import (
    init_consent, get_consent_status,
    fetch_consent, notify_consent
)
from app.database.connection import get_db

router = APIRouter(prefix="/consent", tags=["consent"])

@router.post("/init", response_model=ConsentInitResponse)
async def init_consent_endpoint(
    body: ConsentInitRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return ConsentInitResponse(**(await init_consent(body.patientId, body.hipId, body.purpose.dict(), db)))

@router.get("/status/{consentRequestId}", response_model=ConsentStatusResponse)
async def get_status_endpoint(
    consentRequestId: str,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    consent = await get_consent_status(consentRequestId, db)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent request not found")
    return ConsentStatusResponse(**consent)

@router.post("/fetch", response_model=ConsentFetchResponse)
async def fetch_consent_endpoint(
    body: ConsentFetchRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    consent = await fetch_consent(body.consentRequestId, db)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return ConsentFetchResponse(**consent)

@router.post("/notify")
async def notify_consent_endpoint(
    body: ConsentNotifyRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return await notify_consent(body.consentRequestId, body.status, db)
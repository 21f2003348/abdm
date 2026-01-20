from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.headers import require_gateway_headers
from app.deps.auth import get_current_token
from app.api.schemas import (
    LinkTokenRequest, LinkTokenResponse,
    LinkCareContextRequest, LinkCareContextResponse,
    DiscoverPatientRequest, DiscoverPatientResponse,
    LinkInitRequest, LinkInitResponse,
    LinkConfirmRequest, LinkConfirmResponse,
    LinkNotifyRequest
)
from app.services.linking_service import (
    generate_link_token, link_care_contexts,
    discover_patient, init_link, confirm_link, notify_link
)
from app.database.connection import get_db

router = APIRouter(prefix="/link", tags=["linking"])

@router.post("/token/generate", response_model=LinkTokenResponse)
async def generate_token(
    body: LinkTokenRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return LinkTokenResponse(**(await generate_link_token(body.patientId, body.hipId, db)))

@router.post("/carecontext", response_model=LinkCareContextResponse)
async def link_carecontext(
    body: LinkCareContextRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return LinkCareContextResponse(**(await link_care_contexts(body.patientId, [cc.dict() for cc in body.careContexts], db)))

@router.post("/discover", response_model=DiscoverPatientResponse)
async def discover(
    body: DiscoverPatientRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return DiscoverPatientResponse(**(await discover_patient(body.mobile, body.name, db)))

@router.post("/init", response_model=LinkInitResponse)
async def init(
    body: LinkInitRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return LinkInitResponse(**(await init_link(body.patientId, body.txnId, db)))

@router.post("/confirm", response_model=LinkConfirmResponse)
async def confirm(
    body: LinkConfirmRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return LinkConfirmResponse(**(await confirm_link(body.patientId, body.txnId, body.otp, db)))

@router.post("/notify")
async def notify(
    body: LinkNotifyRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    return await notify_link(body.txnId, body.status, db)

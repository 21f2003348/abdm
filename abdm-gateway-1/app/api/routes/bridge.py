from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.headers import require_gateway_headers
from app.deps.auth import get_current_token
from app.api.schemas import (
    BridgeRegisterRequest, BridgeRegisterResponse,
    BridgeUrlUpdateRequest, BridgeUrlUpdateResponse,
    BridgeService, BridgeServiceRegisterRequest, BridgeServiceRegisterResponse
)
from app.services.bridge_service import (
    register_bridge, get_bridge, update_bridge_url,
    get_services_by_bridge, get_service_by_id,
    register_bridge_service
)
from app.database.connection import get_db

router = APIRouter(prefix="/bridge", tags=["bridge"])

@router.post("/register", response_model=BridgeRegisterResponse)
async def register_bridge_endpoint(
    body: BridgeRegisterRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    # token is validated: proceed to register bridge
    data = await register_bridge(body.bridgeId, body.entityType, body.name, db)
    return BridgeRegisterResponse(
        bridgeId=data["bridgeId"],
        entityType=data["entityType"],
        name=data["name"]
    )

@router.get("/{bridge_id}", response_model=BridgeRegisterResponse)
async def get_bridge_endpoint(
    bridge_id: str,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """Get bridge details by ID, including webhook URL configuration."""
    data = await get_bridge(bridge_id, db)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Bridge not found")
    return BridgeRegisterResponse(
        bridgeId=data["bridgeId"],
        entityType=data["entityType"],
        name=data["name"]
    )

@router.patch("/url", response_model=BridgeUrlUpdateResponse)
async def update_url_endpoint(
    body: BridgeUrlUpdateRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    updated = await update_bridge_url(body.bridgeId, str(body.webhookUrl), db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Bridge not found")
    return BridgeUrlUpdateResponse(bridgeId=updated["bridgeId"], webhookUrl=updated["webhookUrl"])

@router.get("/{bridge_id}/services", response_model=list[BridgeService])
async def list_services_endpoint(
    bridge_id: str,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    services = await get_services_by_bridge(bridge_id, db)
    return [BridgeService(**svc) for svc in services]

@router.get("/service/{service_id}", response_model=BridgeService)
async def get_service_endpoint(
    service_id: str,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    svc = await get_service_by_id(service_id, db)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Service not found")
    return BridgeService(**svc)

@router.post("/service", response_model=BridgeServiceRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_service_endpoint(
    body: BridgeServiceRegisterRequest,
    token=Depends(get_current_token),
    headers=Depends(require_gateway_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new service for a bridge.
    """
    try:
        service = await register_bridge_service(
            bridge_id=body.bridgeId,
            service_id=body.serviceId,
            service_name=body.serviceName,
            service_type=body.serviceType,
            description=body.description,
            db=db
        )
        return BridgeServiceRegisterResponse(**service)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
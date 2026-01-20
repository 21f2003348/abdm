from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import Bridge, BridgeService


async def register_bridge(bridge_id: str, entity_type: str, name: str, db: AsyncSession) -> Dict:
    """Register a new bridge in the database."""
    # Check if bridge already exists
    result = await db.execute(select(Bridge).where(Bridge.bridge_id == bridge_id))
    existing = result.scalar()
    
    if existing:
        return {
            "bridgeId": existing.bridge_id,
            "entityType": existing.entity_type,
            "name": existing.name,
            "webhookUrl": existing.webhook_url
        }
    
    # Create new bridge
    new_bridge = Bridge(
        bridge_id=bridge_id,
        entity_type=entity_type,
        name=name
    )
    db.add(new_bridge)
    await db.commit()
    
    return {
        "bridgeId": new_bridge.bridge_id,
        "entityType": new_bridge.entity_type,
        "name": new_bridge.name,
        "webhookUrl": new_bridge.webhook_url
    }


async def get_bridge(bridge_id: str, db: AsyncSession) -> Optional[Dict]:
    """Get bridge details by ID."""
    result = await db.execute(select(Bridge).where(Bridge.bridge_id == bridge_id))
    bridge = result.scalar()
    
    if not bridge:
        return None
    
    return {
        "bridgeId": bridge.bridge_id,
        "entityType": bridge.entity_type,
        "name": bridge.name,
        "webhookUrl": bridge.webhook_url
    }


async def update_bridge_url(bridge_id: str, url: str, db: AsyncSession) -> Optional[Dict]:
    """Update the webhook URL for a bridge."""
    from loguru import logger
    
    logger.info(f"[PATCH] update_bridge_url called: bridge_id={bridge_id}, url={url}")
    
    # Query for bridge
    result = await db.execute(select(Bridge).where(Bridge.bridge_id == bridge_id))
    bridge = result.scalar()
    
    logger.info(f"[PATCH] Found bridge: {bridge is not None}")
    
    if not bridge:
        logger.error(f"[PATCH] Bridge {bridge_id} not found!")
        return None
    
    logger.info(f"[PATCH] Before update - webhook_url: {bridge.webhook_url}")
    
    # Update the webhook URL
    bridge.webhook_url = url
    logger.info(f"[PATCH] Assigned new webhook_url: {bridge.webhook_url}")
    
    # Add to session and commit
    db.add(bridge)
    logger.info(f"[PATCH] Added bridge to session")
    
    await db.commit()
    logger.info(f"[PATCH] Database committed")
    
    # Refresh to get the updated value
    await db.refresh(bridge)
    logger.info(f"[PATCH] After refresh - webhook_url: {bridge.webhook_url}")
    
    result_dict = {
        "bridgeId": bridge.bridge_id,
        "webhookUrl": bridge.webhook_url
    }
    
    logger.info(f"[PATCH] Returning: {result_dict}")
    return result_dict


async def get_services_by_bridge(bridge_id: str, db: AsyncSession) -> List[Dict]:
    """Get all services for a specific bridge."""
    result = await db.execute(
        select(BridgeService).where(BridgeService.bridge_id == bridge_id)
    )
    services = result.scalars().all()
    
    return [
        {
            "id": svc.service_id,
            "bridgeId": svc.bridge_id,
            "name": svc.service_name,
            "type": svc.service_type,
            "description": svc.description
        }
        for svc in services
    ]


async def get_service_by_id(service_id: str, db: AsyncSession) -> Optional[Dict]:
    """Get a specific service by ID."""
    result = await db.execute(
        select(BridgeService).where(BridgeService.service_id == service_id)
    )
    service = result.scalar()
    
    if not service:
        return None
    
    return {
        "id": service.service_id,
        "bridgeId": service.bridge_id,
        "name": service.service_name,
        "type": service.service_type,
        "description": service.description
    }


async def register_bridge_service(
    bridge_id: str, service_id: str, service_name: str,
    service_type: str, description: str, db: AsyncSession
) -> Dict:
    """Register a service for a bridge."""
    # Check if bridge exists
    bridge_result = await db.execute(
        select(Bridge).where(Bridge.bridge_id == bridge_id)
    )
    bridge = bridge_result.scalar()
    
    if not bridge:
        raise ValueError(f"Bridge {bridge_id} not found")
    
    # Check if service already exists
    service_result = await db.execute(
        select(BridgeService).where(BridgeService.service_id == service_id)
    )
    existing_service = service_result.scalar()
    
    if existing_service:
        # Return existing service (idempotent)
        return {
            "serviceId": existing_service.service_id,
            "bridgeId": existing_service.bridge_id,
            "serviceName": existing_service.service_name,
            "serviceType": existing_service.service_type,
            "description": existing_service.description
        }
    
    # Create new service
    new_service = BridgeService(
        service_id=service_id,
        bridge_id=bridge_id,
        service_name=service_name,
        service_type=service_type,
        description=description
    )
    db.add(new_service)
    await db.commit()
    await db.refresh(new_service)
    
    return {
        "serviceId": new_service.service_id,
        "bridgeId": new_service.bridge_id,
        "serviceName": new_service.service_name,
        "serviceType": new_service.service_type,
        "description": new_service.description
    }
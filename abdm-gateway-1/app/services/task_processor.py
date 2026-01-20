"""
Background task processor for webhook retries and async operations.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import DataTransfer, Bridge
from app.utils.encryption import encryptor
from loguru import logger


class TaskProcessor:
    """Process background tasks for data requests and webhook retries."""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """Start background task processor."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._process_loop())
            logger.info("Background task processor started")
    
    async def stop(self):
        """Stop background task processor."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("Background task processor stopped")
    
    async def _process_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                async with async_session() as db:
                    # Process pending webhook retries
                    await self._process_webhook_retries(db)
                    
                    # Clean up expired data
                    await self._cleanup_expired_data(db)
                    
                    await db.commit()
                
                # Sleep for 30 seconds between cycles
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task processor loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_webhook_retries(self, db: AsyncSession):
        """Process pending webhook retries."""
        now = datetime.utcnow()
        
        # Find transfers ready for retry
        stmt = select(DataTransfer).where(
            and_(
                DataTransfer.status == "READY",
                DataTransfer.retry_count < DataTransfer.max_retries,
                DataTransfer.next_retry_at <= now
            )
        )
        
        result = await db.execute(stmt)
        transfers = result.scalars().all()
        
        for transfer in transfers:
            await self._retry_webhook_delivery(db, transfer)
    
    async def _retry_webhook_delivery(self, db: AsyncSession, transfer: DataTransfer):
        """Retry webhook delivery to HIU."""
        try:
            # Get HIU bridge info
            stmt = select(Bridge).where(Bridge.bridge_id == transfer.to_entity)
            result = await db.execute(stmt)
            hiu_bridge = result.scalar_one_or_none()
            
            if not hiu_bridge or not hiu_bridge.webhook_url:
                logger.warning(f"No webhook URL for HIU {transfer.to_entity}")
                transfer.status = "FAILED"
                transfer.last_webhook_error = "HIU webhook URL not configured"
                return
            
            # Prepare webhook payload in the format Hospital 1 (HIU) expects
            webhook_payload = {
                "requestId": transfer.transfer_id,
                "status": "SUCCESS",
                "encryptedData": transfer.encrypted_data,
                "dataCount": transfer.data_count,
                "expiresAt": transfer.expires_at.isoformat() if transfer.expires_at else datetime.utcnow().isoformat()
            }
            
            logger.info(f"Sending webhook to HIU {transfer.to_entity}: {hiu_bridge.webhook_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    hiu_bridge.webhook_url,
                    json=webhook_payload
                )
                response.raise_for_status()
            
            # Success - mark as delivered
            transfer.status = "DELIVERED"
            transfer.webhook_attempts += 1
            transfer.encrypted_data = None  # Clear data after delivery
            
            logger.info(f"Successfully delivered data for request {transfer.transfer_id} to HIU {transfer.to_entity}")
            
        except Exception as e:
            # Failed - schedule retry
            transfer.retry_count += 1
            transfer.webhook_attempts += 1
            transfer.last_webhook_error = str(e)
            
            if transfer.retry_count >= transfer.max_retries:
                transfer.status = "FAILED"
                logger.error(f"Max retries reached for request {transfer.transfer_id}")
            else:
                # Exponential backoff: 5min, 15min, 45min
                retry_delay = 5 * (3 ** transfer.retry_count)
                transfer.next_retry_at = datetime.utcnow() + timedelta(minutes=retry_delay)
                logger.warning(f"Webhook delivery failed for {transfer.transfer_id}, retry {transfer.retry_count}/{transfer.max_retries} scheduled")
    
    async def _cleanup_expired_data(self, db: AsyncSession):
        """Clean up expired encrypted data."""
        now = datetime.utcnow()
        
        stmt = select(DataTransfer).where(
            and_(
                DataTransfer.expires_at <= now,
                DataTransfer.encrypted_data.isnot(None)
            )
        )
        
        result = await db.execute(stmt)
        expired = result.scalars().all()
        
        for transfer in expired:
            transfer.encrypted_data = None
            transfer.status = "EXPIRED" if transfer.status == "READY" else transfer.status
            logger.info(f"Cleaned up expired data for request {transfer.transfer_id}")
    
    async def send_hip_data_request(
        self,
        db: AsyncSession,
        transfer_id: str,
        hip_id: str,
        patient_id: str,
        consent_id: str,
        care_context_ids: list[str],
        data_types: list[str]
    ) -> bool:
        """
        Send data request to HIP webhook.
        
        Args:
            db: Database session
            transfer_id: Unique transfer request ID
            hip_id: HIP bridge ID
            patient_id: Patient identifier
            consent_id: Consent request ID
            care_context_ids: List of care context IDs
            data_types: List of data types requested
            
        Returns:
            True if webhook sent successfully
        """
        try:
            # Get HIP bridge info
            stmt = select(Bridge).where(Bridge.bridge_id == hip_id)
            result = await db.execute(stmt)
            hip_bridge = result.scalar_one_or_none()
            
            if not hip_bridge or not hip_bridge.webhook_url:
                logger.error(f"No webhook URL for HIP {hip_id}")
                return False
            
            # Prepare webhook payload in the format Hospital 2 expects
            webhook_payload = {
                "requestId": transfer_id,
                "requestType": "HEALTH_DATA_REQUEST",
                "patientId": patient_id,
                "consentId": consent_id,
                "careContextIds": care_context_ids,
                "dataTypes": data_types,
                "hipId": hip_id,
                "hiuId": "hiu-001"
            }
            
            logger.info(f"Sending webhook to HIP {hip_id}: {webhook_payload}")
            
            # Send webhook to HIP
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    hip_bridge.webhook_url,
                    json=webhook_payload
                )
                response.raise_for_status()
            
            logger.info(f"Successfully sent data request {transfer_id} to HIP {hip_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send data request to HIP {hip_id}: {e}")
            return False


# Singleton instance
task_processor = TaskProcessor()

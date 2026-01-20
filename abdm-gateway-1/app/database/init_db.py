import asyncio
import sys
from pathlib import Path
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import engine, async_session
from app.database.models import (
    Base, Client, Bridge, BridgeService, Patient,
    LinkingRequest, LinkedCareContext, ConsentRequest, DataTransfer
)


async def init_db():
    """Initialize database and create tables."""
    async with engine.begin() as conn:
        # Drop all tables first (for development)
        await conn.run_sync(Base.metadata.drop_all)
        # Recreate all tables with new schema
        await conn.run_sync(Base.metadata.create_all)


async def seed_clients():
    """Add dummy client data to the database."""
    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(Client))
        existing = result.scalars().all()
        
        if existing:
            print("Clients already exist in the database.")
            return
        
        dummy_clients = [
            Client(client_id="client-001", client_secret="secret-001"),
            Client(client_id="client-002", client_secret="secret-002"),
            Client(client_id="hospital-abdm", client_secret="hospital-secret-123"),
            Client(client_id="test-client", client_secret="test-secret"),
        ]
        
        session.add_all(dummy_clients)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_clients)} dummy clients.")


async def seed_bridges():
    """Add dummy bridge data to the database."""
    async with async_session() as session:
        result = await session.execute(select(Bridge))
        existing = result.scalars().all()
        
        if existing:
            print("Bridges already exist in the database.")
            return
        
        dummy_bridges = [
            Bridge(
                bridge_id="hip-001",
                entity_type="HIP",
                name="Hospital A",
                webhook_url="http://localhost:8080/webhook"
            ),
            Bridge(
                bridge_id="hip-002",
                entity_type="HIP",
                name="Hospital B",
                webhook_url="http://localhost:8081/webhook"
            ),
            Bridge(
                bridge_id="hiu-001",
                entity_type="HIU",
                name="Insurance Provider",
                webhook_url="http://insurance.local/webhook"
            ),
        ]
        
        session.add_all(dummy_bridges)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_bridges)} dummy bridges.")


async def seed_bridge_services():
    """Add dummy bridge service data to the database."""
    async with async_session() as session:
        result = await session.execute(select(BridgeService))
        existing = result.scalars().all()
        
        if existing:
            print("Bridge services already exist in the database.")
            return
        
        dummy_services = [
            BridgeService(
                service_id="svc-001",
                bridge_id="hip-001",
                service_name="Lab Services",
                service_type="LAB",
                description="Laboratory test results"
            ),
            BridgeService(
                service_id="svc-002",
                bridge_id="hip-001",
                service_name="Pharmacy",
                service_type="PHARMACY",
                description="Prescription and medication records"
            ),
            BridgeService(
                service_id="svc-003",
                bridge_id="hip-002",
                service_name="Radiology",
                service_type="IMAGING",
                description="X-ray and imaging reports"
            ),
            BridgeService(
                service_id="svc-004",
                bridge_id="hiu-001",
                service_name="Claims Processing",
                service_type="CLAIMS",
                description="Insurance claims processing"
            ),
        ]
        
        session.add_all(dummy_services)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_services)} dummy bridge services.")


async def seed_patients():
    """Add dummy patient data to the database."""
    async with async_session() as session:
        result = await session.execute(select(Patient))
        existing = result.scalars().all()
        
        if existing:
            print("Patients already exist in the database.")
            return
        
        from datetime import datetime
        dummy_patients = [
            Patient(
                abha_id="patient-001@abdm",
                abha_address="john.doe@abdm",
                name="John Doe",
                mobile="9876543210",
                gender="Male",
                date_of_birth=datetime(1990, 5, 15)
            ),
            Patient(
                abha_id="patient-002@abdm",
                abha_address="jane.smith@abdm",
                name="Jane Smith",
                mobile="9876543211",
                gender="Female",
                date_of_birth=datetime(1985, 8, 22)
            ),
            Patient(
                abha_id="patient-003@abdm",
                abha_address="raj.kumar@abdm",
                name="Raj Kumar",
                mobile="9876543212",
                gender="Male",
                date_of_birth=datetime(1978, 12, 10)
            ),
        ]
        
        session.add_all(dummy_patients)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_patients)} dummy patients.")


async def seed_linking_requests():
    """Add dummy linking request data to the database."""
    async with async_session() as session:
        result = await session.execute(select(LinkingRequest))
        existing = result.scalars().all()
        
        if existing:
            print("Linking requests already exist in the database.")
            return
        
        dummy_linking = [
            LinkingRequest(
                txn_id=str(uuid.uuid4()),
                patient_abha_id="patient-001@abdm",
                hip_id="hip-001",
                mobile="9876543210",
                status="LINKED",
                link_token="token-12345"
            ),
            LinkingRequest(
                txn_id=str(uuid.uuid4()),
                patient_abha_id="patient-002@abdm",
                hip_id="hip-002",
                mobile="9876543211",
                status="INITIATED",
                link_token=None
            ),
        ]
        
        session.add_all(dummy_linking)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_linking)} dummy linking requests.")


async def seed_linked_care_contexts():
    """Add dummy linked care context data to the database."""
    async with async_session() as session:
        result = await session.execute(select(LinkedCareContext))
        existing = result.scalars().all()
        
        if existing:
            print("Linked care contexts already exist in the database.")
            return
        
        dummy_care_contexts = [
            LinkedCareContext(
                patient_abha_id="patient-001@abdm",
                care_context_id="cc-001",
                reference_number="OPD-2025-001",
                hip_id="hip-001"
            ),
            LinkedCareContext(
                patient_abha_id="patient-001@abdm",
                care_context_id="cc-002",
                reference_number="IPD-2025-001",
                hip_id="hip-001"
            ),
            LinkedCareContext(
                patient_abha_id="patient-002@abdm",
                care_context_id="cc-003",
                reference_number="OPD-2025-002",
                hip_id="hip-002"
            ),
        ]
        
        session.add_all(dummy_care_contexts)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_care_contexts)} dummy linked care contexts.")


async def seed_consent_requests():
    """Add dummy consent request data to the database."""
    async with async_session() as session:
        result = await session.execute(select(ConsentRequest))
        existing = result.scalars().all()
        
        if existing:
            print("Consent requests already exist in the database.")
            return
        
        dummy_consents = [
            ConsentRequest(
                consent_request_id="consent-001",
                patient_abha_id="patient-001@abdm",
                hip_id="hip-001",
                purpose={"code": "TREATMENT", "text": "Treatment purpose"},
                status="APPROVED"
            ),
            ConsentRequest(
                consent_request_id="consent-002",
                patient_abha_id="patient-002@abdm",
                hip_id="hip-002",
                purpose={"code": "COVERAGE", "text": "Insurance coverage"},
                status="INITIATED"
            ),
        ]
        
        session.add_all(dummy_consents)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_consents)} dummy consent requests.")


async def seed_data_transfers():
    """Add dummy data transfer data to the database."""
    async with async_session() as session:
        result = await session.execute(select(DataTransfer))
        existing = result.scalars().all()
        
        if existing:
            print("Data transfers already exist in the database.")
            return
        
        dummy_transfers = [
            DataTransfer(
                transfer_id="transfer-001",
                consent_request_id="consent-001",
                patient_abha_id="patient-001@abdm",
                from_entity="hip-001",
                to_entity="hiu-001",
                status="READY",
                data_count=3
            ),
            DataTransfer(
                transfer_id=str(uuid.uuid4()),
                consent_request_id="consent-002",
                patient_abha_id="patient-002@abdm",
                from_entity="hip-002",
                to_entity="hiu-001",
                status="PENDING",
                data_count=0
            ),
        ]
        
        session.add_all(dummy_transfers)
        await session.commit()
        print(f"✓ Successfully seeded {len(dummy_transfers)} dummy data transfers.")


async def main():
    """Initialize database and seed all data."""
    print("=" * 50)
    print("Initializing ABDM Gateway Database")
    print("=" * 50)
    
    print("\n[1/2] Creating database tables...")
    await init_db()
    print("✓ Database tables created successfully!")
    
    print("\n[2/2] Seeding dummy data...")
    await seed_clients()
    await seed_bridges()
    await seed_bridge_services()
    await seed_patients()  # Seed patients first before other tables reference them
    await seed_linking_requests()
    await seed_linked_care_contexts()
    await seed_consent_requests()
    await seed_data_transfers()
    
    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

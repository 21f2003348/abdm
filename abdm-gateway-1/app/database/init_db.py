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
    """Initialize database and create tables if they don't exist."""
    async with engine.begin() as conn:
        # Only create tables if they don't exist (don't drop existing data)
        await conn.run_sync(Base.metadata.create_all)


async def seed_clients():
    """Add client credentials to the database."""
    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(Client))
        existing = result.scalars().all()
        
        if existing:
            print("Clients already exist in the database.")
            return
        
        # Add client credentials for hospital authentication
        client_credentials = [
            Client(client_id="client-001", client_secret="secret-001"),
            Client(client_id="client-002", client_secret="secret-002"),
            Client(client_id="hospital-abdm", client_secret="hospital-secret-123"),
            Client(client_id="test-client", client_secret="test-secret"),
        ]
        
        session.add_all(client_credentials)
        await session.commit()
        print(f"✓ Successfully seeded {len(client_credentials)} client credentials.")


# =============================================================================
# The following seed functions are DISABLED - gateway will auto-populate data
# from hospital registrations. Uncomment if needed for testing.
# =============================================================================


async def main():
    """Initialize database and seed only client credentials."""
    print("=" * 50)
    print("Initializing ABDM Gateway Database")
    print("=" * 50)
    
    print("\n[1/2] Creating database tables...")
    await init_db()
    print("✓ Database tables created successfully!")
    
    print("\n[2/2] Seeding client credentials...")
    await seed_clients()
    print("✓ Client credentials seeded!")
    
    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("Gateway will auto-populate data from hospital registrations")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

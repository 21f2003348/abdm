from app.core.config import get_settings
from app.core.security import create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import Client
from app.database.connection import get_db

settings = get_settings()

async def validate_client_credentials(client_id: str, client_secret: str, db: AsyncSession) -> bool:
    query = select(Client).where(Client.client_id == client_id, Client.client_secret == client_secret)
    result = await db.execute(query)
    client = result.scalar()
    return client is not None

def issue_access_token(client_id: str, cm_id: str) -> str:
    token = create_access_token({"clientId": client_id, "cmId": cm_id})
    return {
        "accessToken": token,
        "expiresIn": settings.jwt_expiry_seconds,
        "tokenType": "Bearer"
    }
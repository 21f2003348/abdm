import time 
import jwt 
from typing import Any 

from app.core.config import get_settings

settings = get_settings()

def create_access_token(payload: dict[str, Any]) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = int(time.time()) + settings.jwt_expiry_seconds
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_alg)

def decode_access_token(token:str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
from fastapi import Depends, HTTPException, status # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # type: ignore

from app.core.security import decode_access_token 

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token"
        )
    
    token = credentials.credentials

    try:
        return decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
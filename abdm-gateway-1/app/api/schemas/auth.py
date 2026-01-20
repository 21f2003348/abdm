from pydantic import BaseModel

class SessionRequest(BaseModel):
    clientId: str
    clientSecret: str
    grantType: str

class SessionResponse(BaseModel):
    accessToken: str
    expiresIn: int
    tokenType: str = "Bearer"
from pydantic import BaseModel

class AuthSessionRequest(BaseModel):
    client_id: str
    client_secret: str

class RegisterBridgeRequest(BaseModel):
    bridgeId: str
    entityType: str
    name: str

class UpdateBridgeWebhookRequest(BaseModel):
    bridgeId: str
    webhookUrl: str
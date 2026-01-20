from typing import Literal
from pydantic import BaseModel, HttpUrl

class BridgeRegisterRequest(BaseModel):
    bridgeId: str
    entityType: Literal["HIP", "HIU"]
    name: str

class BridgeRegisterResponse(BaseModel):
    bridgeId: str
    entityType: str
    name: str

class BridgeUrlUpdateRequest(BaseModel):
    bridgeId: str
    webhookUrl: HttpUrl

class BridgeUrlUpdateResponse(BaseModel):
    bridgeId: str
    webhookUrl: HttpUrl

class BridgeService(BaseModel):
    id: str
    name: str
    active: bool = True
    version: str = "v1"

class BridgeServiceRegisterRequest(BaseModel):
    bridgeId: str
    serviceId: str
    serviceName: str
    serviceType: str
    description: str = None

class BridgeServiceRegisterResponse(BaseModel):
    serviceId: str
    bridgeId: str
    serviceName: str
    serviceType: str
    description: str = None
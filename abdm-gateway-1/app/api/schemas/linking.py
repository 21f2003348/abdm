from typing import List, Optional
from pydantic import BaseModel

class LinkTokenRequest(BaseModel):
    patientId: str
    hipId: str

class LinkTokenResponse(BaseModel):
    token: str
    expiresIn: int = 300
    txnId: str

class CareContext(BaseModel):
    id: str
    referenceNumber: str

class LinkCareContextRequest(BaseModel):
    patientId: str
    careContexts: List[CareContext]

class LinkCareContextResponse(BaseModel):
    status: str = "PENDING"

class DiscoverPatientRequest(BaseModel):
    mobile: str
    name: str = None

class DiscoverPatientResponse(BaseModel):
    patientId: str
    status: str = "FOUND"

class LinkInitRequest(BaseModel):
    patientId: str
    txnId: str

class LinkInitResponse(BaseModel):
    status: str = "INITIATED"
    txnId: str

class LinkConfirmRequest(BaseModel):
    patientId: str
    txnId: str
    otp: str

class LinkConfirmResponse(BaseModel):
    status: str = "CONFIRMED"
    txnId: str

class LinkNotifyRequest(BaseModel):
    txnId: str
    status: str
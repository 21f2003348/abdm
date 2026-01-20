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
    hipId: str = None  # Hospital ID (optional but recommended)

class LinkCareContextRequest(BaseModel):
    patientId: str
    careContexts: List[CareContext]

class LinkCareContextResponse(BaseModel):
    status: str = "PENDING"

class DiscoverPatientRequest(BaseModel):
    mobile: str
    name: str = None
    gender: str = None  # Male, Female, Other
    dateOfBirth: str = None  # ISO date string
    aadhaar: str = None

class DiscoverPatientResponse(BaseModel):
    patientId: str
    abhaId: str = None
    status: str = "FOUND"
    gender: str = None
    dateOfBirth: str = None
    abhaAddress: str = None

class LinkInitRequest(BaseModel):
    patientId: str
    txnId: str
    hipId: str = "HOSPITAL-1"  # Default to HOSPITAL-1, but should be provided

class LinkInitResponse(BaseModel):
    status: str = "LINKED"
    txnId: str
    token: str = None

class LinkConfirmRequest(BaseModel):
    patientId: str
    txnId: str
    otp: str
    hipId: str = "HOSPITAL-1"  # Default to HOSPITAL-1, but should be provided

class LinkConfirmResponse(BaseModel):
    status: str = "CONFIRMED"
    txnId: str

class LinkNotifyRequest(BaseModel):
    txnId: str
    status: str
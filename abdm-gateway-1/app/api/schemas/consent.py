from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class ConsentPurpose(BaseModel):
    code: str
    text: str

class ConsentInitRequest(BaseModel):
    patientId: str
    hipId: str
    purpose: ConsentPurpose
    dataRange: Optional[dict] = None

class ConsentInitResponse(BaseModel):
    consentRequestId: str
    status: str = "INITIATED"

class ConsentStatusResponse(BaseModel):
    consentRequestId: str
    status: str
    createdAt: Optional[str] = None

class ConsentFetchRequest(BaseModel):
    consentRequestId: str

class ConsentFetchResponse(BaseModel):
    consentRequestId: str
    status: str
    consentArtefact: Optional[dict] = None

class ConsentNotifyRequest(BaseModel):
    consentRequestId: str
    status: str
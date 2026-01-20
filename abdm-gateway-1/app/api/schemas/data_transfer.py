from typing import Optional, List
from pydantic import BaseModel

class HealthInfoMetadata(BaseModel):
    type: str  # "DiagnosticReport", "Prescription", etc.
    createdAt: str

class EncryptedHealthInfo(BaseModel):
    encryptedData: str
    keyMaterial: str

class SendHealthInfoRequest(BaseModel):
    txnId: str
    patientId: str
    hipId: str
    careContextId: str
    healthInfo: EncryptedHealthInfo
    metadata: HealthInfoMetadata

class SendHealthInfoResponse(BaseModel):
    status: str = "RECEIVED"
    txnId: str

class RequestHealthInfoRequest(BaseModel):
    patientId: str
    hipId: str
    careContextId: str
    dataTypes: List[str]

class RequestHealthInfoResponse(BaseModel):
    requestId: str
    status: str  = "REQUESTED" # "REQUESTED", "FAILED", etc.

class DataFlowNotifyRequest(BaseModel):
    txnId: str
    status: str
    hipId: str

class DataFlowNotifyResponse(BaseModel):
    status: str  = "ACKNOWLEDGED" # "NOTIFIED", "FAILED", etc.
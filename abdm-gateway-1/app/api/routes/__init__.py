from fastapi import APIRouter
from app.api.routes import auth, bridge, linking, consent, data_transfer, communication, patients

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(bridge.router)
api_router.include_router(patients.router)
api_router.include_router(linking.router)
api_router.include_router(consent.router)
api_router.include_router(data_transfer.router)
api_router.include_router(communication.router)

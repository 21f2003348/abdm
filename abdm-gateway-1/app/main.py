from contextlib import asynccontextmanager
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger 

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.routes import api_router
from app.database.init_db import (
    init_db, seed_clients, seed_bridges, seed_bridge_services, seed_patients,
    seed_linking_requests, seed_linked_care_contexts, seed_consent_requests,
    seed_data_transfers
)
from app.services.task_processor import task_processor

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting ABDM Gateway on {settings.app_host}:{settings.app_port}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("Initializing database...")
    await init_db()
    await seed_clients()
    await seed_bridges()
    await seed_bridge_services()
    await seed_patients()
    await seed_linking_requests()
    await seed_linked_care_contexts()
    await seed_consent_requests()
    await seed_data_transfers()
    logger.info("Database initialized with all dummy data.")
    
    # Start background task processor for webhook retries
    logger.info("Starting background task processor...")
    await task_processor.start()
    logger.info("Background task processor started.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ABDM Gateway")
    await task_processor.stop()
    logger.info("Background task processor stopped.")


app = FastAPI(
    title="ABDM Gateway",
    description="API Gateway for ABDM services with background task processing",
    version="0.2.0",
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests from hospital and other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "abdm-gateway"}

@app.get("/hello")
async def hello():
    return {"message": "Hello, ABDM Gateway!"}


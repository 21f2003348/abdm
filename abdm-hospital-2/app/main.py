from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.services.gateway_service import gateway_health_check, create_auth_session, register_bridge, update_bridge_webhook
from app.api.models import AuthSessionRequest, RegisterBridgeRequest, UpdateBridgeWebhookRequest
from app.api.routes import patient, visit, care_context, webhook, demo, health_records, data_requests
import os

app = FastAPI(
    title="ABDM Hospital System",
    description="Hospital Information System integrated with ABDM Gateway",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "abdm-hospital"}

@app.get("/gateway-health")
async def check_gateway_health():
    """Endpoint to check the health of the ABDM Gateway."""
    return await gateway_health_check()

@app.get("/test-auth-session")
async def test_auth_session():
    """
    Test the create_auth_session function by calling the /api/auth/session endpoint.
    """
    return await create_auth_session()

@app.post("/test-register-bridge")
async def test_register_bridge():
    """
    Test the register_bridge function by calling the /api/bridge/register endpoint.
    """
    return await register_bridge()   

@app.patch("/test-update-bridge-webhook")
async def test_update_bridge_webhook():
    """
    Test the update_bridge_webhook function by calling the /api/bridge/update-webhook endpoint.
    """
    return await update_bridge_webhook()

app.include_router(patient.router)
app.include_router(visit.router)
app.include_router(care_context.router)
app.include_router(webhook.router)
app.include_router(demo.router)
app.include_router(health_records.router)
app.include_router(data_requests.router)

# Serve frontend
@app.get("/")
async def read_root():
    """Serve the frontend application"""
    frontend_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {"message": "ABDM Hospital System API", "docs": "/docs"}

@app.get("/{page}.html")
async def serve_page(page: str):
    """Serve HTML pages from frontend directory"""
    # Check if it's test_api.html (serve from root)
    if page == "test_api":
        root_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_api.html")
        if os.path.exists(root_file):
            return FileResponse(root_file)
    
    # Otherwise serve from frontend directory
    frontend_file = os.path.join(frontend_path, f"{page}.html")
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    raise HTTPException(status_code=404, detail="Page not found")
    frontend_file = os.path.join(frontend_path, f"{page}.html")
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    raise HTTPException(status_code=404, detail="Page not found")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)

# uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
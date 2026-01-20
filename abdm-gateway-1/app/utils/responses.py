from datetime import datetime, timezone 
from typing import Any

def success_response(data: Any, request_id: str) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": data,
        "error": None,
    }

def error_response(code: str, message: str, request_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
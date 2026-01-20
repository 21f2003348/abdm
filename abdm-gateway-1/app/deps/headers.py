from fastapi import Header, HTTPException, status

def require_gateway_headers(
        x_request_id: str | None = Header(default=None, convert_underscores=False, alias="REQUEST-ID"),
        x_timestamp: str | None = Header(default=None, convert_underscores=False, alias="TIMESTAMP"),
        x_cm_id: str | None = Header(default=None, convert_underscores=False, alias="X-CM-ID"),
) -> dict[str, str]:
    
    missing = [name for name, value in {
        "REQUEST-ID": x_request_id,
        "TIMESTAMP": x_timestamp,
        "X-CM-ID": x_cm_id
    }.items() if not value]

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required headers: {', '.join(missing)}",
        )
    
    return {"request_id": x_request_id, "timestamp": x_timestamp, "cm_id": x_cm_id}

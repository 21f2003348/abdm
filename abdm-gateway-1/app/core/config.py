import os 
from functools import lru_cache
from typing import Literal
from dotenv import load_dotenv # type: ignore

load_dotenv()

class Settings:
    def __init__(self):
        self.app_env: Literal["local", "dev", "prod"] = os.getenv("APP_ENV", "local")
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8000"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.cm_id: str = os.getenv("CM_ID", "sbx")
        self.jwt_secret: str = os.getenv("JWT_SECRET", "secret")
        self.jwt_alg: str = os.getenv("JWT_ALG", "HS256")
        self.jwt_expiry_seconds: int = int(os.getenv("JWT_EXPIRY_SECONDS", "900"))

        # Database settings
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./abdm_gateway.db")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
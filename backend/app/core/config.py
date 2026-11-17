from typing import Optional

from pydantic import EmailStr, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "CMS API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./cms.db"

    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    VERCEL_DEPLOY_HOOK: Optional[str] = None

    ADMIN_EMAIL: EmailStr
    ADMIN_PASSWORD: str = Field(..., min_length=8, max_length=72)


try:
    settings = Settings()
except ValidationError as e:
    raise RuntimeError(
        "Faltan variables de entorno. Copia .env.example a .env y llena "
        "SECRET_KEY, ADMIN_EMAIL y ADMIN_PASSWORD."
    ) from e

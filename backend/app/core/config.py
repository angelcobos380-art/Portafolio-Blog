from typing import List, Optional

from pydantic import EmailStr, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "CMS API"
    VERSION: str = "1.3.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./cms.db"

    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4321"

    REBUILD_WEBHOOK_URL: Optional[str] = None
    VERCEL_DEPLOY_HOOK: Optional[str] = None

    STORAGE_BACKEND: str = "local"
    MEDIA_LOCAL_DIR: str = "./uploads"
    MEDIA_BASE_URL: str = "http://localhost:8000/media"
    MEDIA_MAX_BYTES: int = 10_485_760

    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_FOLDER: str = "cms-media"

    ADMIN_EMAIL: EmailStr
    ADMIN_PASSWORD: str = Field(..., min_length=8, max_length=72)

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def rebuild_webhook_url(self) -> Optional[str]:
        return self.REBUILD_WEBHOOK_URL or self.VERCEL_DEPLOY_HOOK


try:
    settings = Settings()
except ValidationError as e:
    raise RuntimeError(
        "Faltan variables de entorno. Copia .env.example a .env y llena "
        "SECRET_KEY, ADMIN_EMAIL y ADMIN_PASSWORD."
    ) from e

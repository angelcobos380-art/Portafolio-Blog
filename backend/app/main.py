from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin.router import admin_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_db_and_tables, seed_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_admin()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CMS API para portafolio y blog construido con FastAPI, Pydantic v2 y SQLModel.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix="/admin")


@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health Check"])
async def health():
    return {"status": "ok"}

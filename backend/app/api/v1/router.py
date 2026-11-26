from fastapi import APIRouter

from app.api.v1.endpoints import auth, media, metrics, posts, projects, public, templates

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(posts.router)
api_router.include_router(templates.router)
api_router.include_router(media.router)
api_router.include_router(projects.router)
api_router.include_router(public.router)
api_router.include_router(metrics.router)

from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, metrics, posts, projects, public

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(posts.router)
api_router.include_router(projects.router)
api_router.include_router(categories.router)
api_router.include_router(public.router)
api_router.include_router(metrics.router)

from fastapi import APIRouter

from app.admin import auth, categories, dashboard, metrics, posts, projects

admin_router = APIRouter()
admin_router.include_router(auth.router)
admin_router.include_router(dashboard.router)
admin_router.include_router(posts.router)
admin_router.include_router(projects.router)
admin_router.include_router(categories.router)
admin_router.include_router(metrics.router)

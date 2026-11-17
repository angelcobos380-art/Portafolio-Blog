from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.admin.deps import get_admin_user, templates
from app.core.database import Category, Post, PostView, Project, ProjectView, get_session

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    posts = session.exec(select(Post)).all()
    projects = session.exec(select(Project)).all()
    categories = session.exec(select(Category)).all()

    post_views = 0
    for post in posts:
        view = session.get(PostView, post.post_id)
        post_views += view.count if view else 0

    project_views = 0
    for project in projects:
        view = session.get(ProjectView, project.project_id)
        project_views += view.count if view else 0

    recent_posts = sorted(posts, key=lambda p: p.created_at, reverse=True)[:5]

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "post_count": len(posts),
        "project_count": len(projects),
        "category_count": len(categories),
        "post_views": post_views,
        "project_views": project_views,
        "recent_posts": recent_posts,
    })

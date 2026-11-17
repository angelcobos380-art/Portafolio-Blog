from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.admin.deps import get_admin_user, templates
from app.core.database import Post, PostView, Project, ProjectView, get_session

router = APIRouter(prefix="/metrics")


@router.get("")
def metrics_view(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    posts = session.exec(select(Post)).all()
    projects = session.exec(select(Project)).all()

    post_rows = []
    total_post_views = 0
    for post in posts:
        view = session.get(PostView, post.post_id)
        count = view.count if view else 0
        total_post_views += count
        post_rows.append({"slug": post.slug, "title": post.title, "views": count})

    project_rows = []
    total_project_views = 0
    for project in projects:
        view = session.get(ProjectView, project.project_id)
        count = view.count if view else 0
        total_project_views += count
        project_rows.append({"slug": project.slug, "title": project.title, "views": count})

    return templates.TemplateResponse(request=request, name="metrics.html", context={
        "total_post_views": total_post_views,
        "total_project_views": total_project_views,
        "posts": post_rows,
        "projects": project_rows,
    })

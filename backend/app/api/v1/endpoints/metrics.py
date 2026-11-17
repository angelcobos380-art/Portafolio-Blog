from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import Post, PostView, Project, ProjectView, get_session
from app.core.security import get_current_user
from app.schemas.metric import MetricsOverview, PostMetricsItem, ProjectMetricsItem
from app.schemas.post import PostStatus
from app.schemas.project import ProjectStatus

router = APIRouter(tags=["Metrics"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/public/posts/{slug}/view", status_code=status.HTTP_204_NO_CONTENT)
def record_post_view(slug: str, session: Session = Depends(get_session)):
    post = session.exec(select(Post).where(Post.slug == slug, Post.status == PostStatus.PUBLICADO.value)).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada.")

    view = session.get(PostView, post.post_id)
    if view is None:
        view = PostView(post_id=post.post_id, count=1)
    else:
        view.count += 1
    view.last_viewed_at = _now()
    session.add(view)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/public/projects/{slug}/view", status_code=status.HTTP_204_NO_CONTENT)
def record_project_view(slug: str, session: Session = Depends(get_session)):
    project = session.exec(select(Project).where(Project.slug == slug, Project.status == ProjectStatus.PUBLICADO.value)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    view = session.get(ProjectView, project.project_id)
    if view is None:
        view = ProjectView(project_id=project.project_id, count=1)
    else:
        view.count += 1
    view.last_viewed_at = _now()
    session.add(view)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/metrics/overview", response_model=MetricsOverview)
def metrics_overview(session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    posts = session.exec(select(Post)).all()
    projects = session.exec(select(Project)).all()

    post_items = []
    total_post_views = 0
    for post in posts:
        view = session.get(PostView, post.post_id)
        views = view.count if view else 0
        total_post_views += views
        post_items.append(PostMetricsItem(
            post_id=post.post_id,
            slug=post.slug,
            title=post.title,
            views=views,
            last_viewed_at=view.last_viewed_at if view else None,
        ))

    project_items = []
    total_project_views = 0
    for project in projects:
        view = session.get(ProjectView, project.project_id)
        views = view.count if view else 0
        total_project_views += views
        project_items.append(ProjectMetricsItem(
            project_id=project.project_id,
            slug=project.slug,
            title=project.title,
            views=views,
            last_viewed_at=view.last_viewed_at if view else None,
        ))

    return MetricsOverview(
        total_post_views=total_post_views,
        total_project_views=total_project_views,
        posts=post_items,
        projects=project_items,
    )


@router.get("/metrics/posts/{post_id}", response_model=PostMetricsItem)
def post_metrics(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    view = session.get(PostView, post_id)
    return PostMetricsItem(
        post_id=post.post_id,
        slug=post.slug,
        title=post.title,
        views=view.count if view else 0,
        last_viewed_at=view.last_viewed_at if view else None,
    )


@router.get("/metrics/projects/{project_id}", response_model=ProjectMetricsItem)
def project_metrics(project_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")
    view = session.get(ProjectView, project_id)
    return ProjectMetricsItem(
        project_id=project.project_id,
        slug=project.slug,
        title=project.title,
        views=view.count if view else 0,
        last_viewed_at=view.last_viewed_at if view else None,
    )

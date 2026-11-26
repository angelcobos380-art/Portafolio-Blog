from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import Post, Project, Template, get_session
from app.schemas.common import PaginatedResponse
from app.schemas.post import PostStatus, PublicPostDetail, PublicPostListItem
from app.schemas.project import ProjectResponse, ProjectStatus
from app.schemas.template import TemplateStatus, TemplateSummary

router = APIRouter(prefix="/public", tags=["Public"])


def _resolve_template(session: Session, post: Post) -> Optional[TemplateSummary]:
    tpl = session.get(Template, post.template_id) if post.template_id else None
    if tpl is None:
        tpl = session.exec(
            select(Template).where(
                Template.is_default == True,  # noqa: E712
                Template.status == TemplateStatus.ACTIVA.value,
            )
        ).first()
    if tpl is None:
        return None
    return TemplateSummary.model_validate(tpl)


@router.get("/posts", response_model=PaginatedResponse[PublicPostListItem])
def list_public_posts(
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    published = session.exec(select(Post).where(Post.status == PostStatus.PUBLICADO.value)).all()

    if tag:
        target = tag.strip().lower()
        published = [p for p in published if target in [t.lower() for t in (p.tags or [])]]

    published.sort(key=lambda p: p.published_at or p.created_at, reverse=True)

    total = len(published)
    start = (page - 1) * page_size
    page_items = [PublicPostListItem.model_validate(p) for p in published[start : start + page_size]]

    return PaginatedResponse[PublicPostListItem](
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/posts/{slug}", response_model=PublicPostDetail)
def get_public_post_by_slug(slug: str, session: Session = Depends(get_session)):
    post = session.exec(
        select(Post).where(Post.slug == slug, Post.status == PostStatus.PUBLICADO.value)
    ).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publicación no encontrada o no disponible públicamente.",
        )

    return PublicPostDetail(
        post_id=post.post_id,
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        cover_image_url=post.cover_image_url,
        seo=post.seo,
        tags=post.tags or [],
        published_at=post.published_at,
        content_html=post.content_html,
        content=post.content,
        template=_resolve_template(session, post),
    )


@router.get("/projects", response_model=List[ProjectResponse])
def list_public_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(Project).where(Project.status == ProjectStatus.PUBLICADO.value)).all()
    return sorted(projects, key=lambda p: (not p.is_featured, p.sort_order))


@router.get("/projects/{slug}", response_model=ProjectResponse)
def get_public_project_by_slug(slug: str, session: Session = Depends(get_session)):
    project = session.exec(
        select(Project).where(Project.slug == slug, Project.status == ProjectStatus.PUBLICADO.value)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")
    return project

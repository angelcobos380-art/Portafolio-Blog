from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import Post, get_session
from app.schemas.post import PostResponse, PostStatus

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/posts")
def list_public_posts(
    category_slug: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session),
):
    published = session.exec(select(Post).where(Post.status == PostStatus.PUBLICADO.value)).all()

    if category_slug:
        published = [p for p in published if p.frozen_category and p.frozen_category.get("slug") == category_slug]
    if tag:
        published = [p for p in published if tag in (p.tags or [])]

    start = (page - 1) * limit
    end = start + limit

    return {
        "total": len(published),
        "page": page,
        "limit": limit,
        "items": published[start:end],
    }


@router.get("/posts/{slug}", response_model=PostResponse)
def get_public_post_by_slug(slug: str, session: Session = Depends(get_session)):
    post = session.exec(
        select(Post).where(Post.slug == slug, Post.status == PostStatus.PUBLICADO.value)
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada o no disponible públicamente.")
    return post

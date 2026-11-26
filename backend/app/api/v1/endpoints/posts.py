from datetime import datetime, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.core.database import Post, Template, get_session
from app.core.deploy import trigger_rebuild
from app.core.sanitizer import extract_plain_text, sanitize_html
from app.core.security import get_current_user
from app.core.utils import slugify
from app.schemas.common import PaginatedResponse
from app.schemas.post import PostCreate, PostListItem, PostResponse, PostStatus, PostUpdate
from app.schemas.template import TemplateStatus

router = APIRouter(prefix="/posts", tags=["Posts"])

ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "published_at", "title"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug_exists(session: Session, slug: str, exclude_post_id: Optional[str] = None) -> bool:
    stmt = select(Post).where(Post.slug == slug)
    if exclude_post_id:
        stmt = stmt.where(Post.post_id != exclude_post_id)
    return session.exec(stmt).first() is not None


def _resolve_auto_slug(session: Session, title: str, exclude_post_id: Optional[str] = None) -> str:
    base = slugify(title) or "borrador"
    candidate = base
    while _slug_exists(session, candidate, exclude_post_id=exclude_post_id):
        candidate = f"{base}-{secrets.token_hex(2)}"
    return candidate


def _validate_template_ref(session: Session, template_id: Optional[str]) -> None:
    if template_id is None:
        return
    template = session.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Plantilla especificada no existe.")
    if template.status != TemplateStatus.ACTIVA.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede asignar una plantilla archivada.",
        )


def _apply_update(
    post: Post,
    post_in: PostUpdate,
    session: Session,
    background_tasks: BackgroundTasks,
) -> Post:
    if post.status == PostStatus.ARCHIVADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un post ARCHIVADO es solo lectura. Restáuralo a BORRADOR para editarlo.",
        )

    fields_set = post_in.model_fields_set

    if "template_id" in fields_set:
        _validate_template_ref(session, post_in.template_id)
        post.template_id = post_in.template_id

    if "slug" in fields_set and post_in.slug is not None:
        normalized_slug = slugify(post_in.slug)
        if not normalized_slug:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El slug proporcionado no es válido.",
            )
        if post.published_at is not None and normalized_slug != post.slug:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede cambiar el slug de un post que ya fue publicado.",
            )
        if _slug_exists(session, normalized_slug, exclude_post_id=post.post_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug ya existe.")
        post.slug = normalized_slug

    if "title" in fields_set and post_in.title is not None:
        title_changed = post_in.title != post.title
        post.title = post_in.title
        if title_changed and post.published_at is None and "slug" not in fields_set:
            post.slug = _resolve_auto_slug(session, post.title, exclude_post_id=post.post_id)

    if "tags" in fields_set:
        post.tags = [slugify(t) for t in (post_in.tags or []) if slugify(t)]

    if "excerpt" in fields_set:
        post.excerpt = post_in.excerpt

    if "cover_image_url" in fields_set:
        post.cover_image_url = post_in.cover_image_url

    if "seo" in fields_set:
        post.seo = post_in.seo.model_dump() if post_in.seo is not None else None

    if "content_json" in fields_set:
        post.content_json = post_in.content_json

    if "content_html" in fields_set:
        post.content_html = sanitize_html(post_in.content_html)

    if "content" in fields_set:
        post.content = post_in.content

    if "content_schema_version" in fields_set:
        post.content_schema_version = post_in.content_schema_version

    post.updated_at = _now()
    session.add(post)
    session.commit()
    session.refresh(post)

    if post.status == PostStatus.PUBLICADO.value:
        background_tasks.add_task(trigger_rebuild)

    return post


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    _validate_template_ref(session, post_in.template_id)

    if post_in.slug is not None:
        resolved_slug = slugify(post_in.slug)
        if not resolved_slug:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El slug proporcionado no es válido.",
            )
        if _slug_exists(session, resolved_slug):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug ya existe.")
    else:
        resolved_slug = _resolve_auto_slug(session, post_in.title)

    clean_tags = [slugify(t) for t in (post_in.tags or []) if slugify(t)]

    post = Post(
        slug=resolved_slug,
        title=post_in.title,
        content=post_in.content,
        content_json=post_in.content_json,
        content_html=sanitize_html(post_in.content_html),
        content_schema_version=post_in.content_schema_version,
        excerpt=post_in.excerpt,
        cover_image_url=post_in.cover_image_url,
        seo=post_in.seo.model_dump() if post_in.seo is not None else None,
        template_id=post_in.template_id,
        tags=clean_tags,
        status=PostStatus.BORRADOR.value,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.get("", response_model=PaginatedResponse[PostListItem])
def list_posts(
    status_filter: Optional[str] = Query(None, alias="status"),
    tag: Optional[str] = None,
    q: Optional[str] = None,
    sort: str = "-updated_at",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    posts = session.exec(select(Post)).all()

    if status_filter:
        allowed_statuses = {s.strip().upper() for s in status_filter.split(",") if s.strip()}
        posts = [p for p in posts if p.status in allowed_statuses]

    if tag:
        target_tag = tag.strip().lower()
        posts = [p for p in posts if target_tag in [t.lower() for t in (p.tags or [])]]

    if q:
        needle = q.strip().lower()
        posts = [p for p in posts if needle in (p.title or "").lower() or needle in (p.slug or "").lower()]

    descending = sort.startswith("-")
    sort_field = sort[1:] if descending else sort
    if sort_field not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campo de orden inválido: {sort_field}.",
        )

    posts.sort(
        key=lambda p: (getattr(p, sort_field) is None, getattr(p, sort_field) or ""),
        reverse=descending,
    )

    total = len(posts)
    start = (page - 1) * page_size
    page_items = [PostListItem.model_validate(p) for p in posts[start : start + page_size]]

    return PaginatedResponse[PostListItem](
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    return post


@router.patch("/{post_id}", response_model=PostResponse)
def patch_post(
    post_id: str,
    post_in: PostUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    return _apply_update(post, post_in, session, background_tasks)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: str,
    post_in: PostUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    return _apply_update(post, post_in, session, background_tasks)


@router.post("/{post_id}/publish", response_model=PostResponse)
def publish_post(
    post_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status != PostStatus.BORRADOR.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transición no permitida desde el estado {post.status}.",
        )

    errors = []
    title_clean = (post.title or "").strip()
    if len(title_clean) < 5 or len(title_clean) > 120:
        errors.append(
            {
                "loc": ["body", "title"],
                "msg": "El título debe tener entre 5 y 120 caracteres para publicar.",
                "type": "value_error",
            }
        )

    plain_text = extract_plain_text(post.content_html, post.content)
    if len(plain_text) < 10:
        errors.append(
            {
                "loc": ["body", "content"],
                "msg": "El contenido debe tener al menos 10 caracteres de texto para publicar.",
                "type": "value_error",
            }
        )

    if not post.slug or _slug_exists(session, post.slug, exclude_post_id=post.post_id):
        errors.append(
            {
                "loc": ["body", "slug"],
                "msg": "El slug debe ser válido y único.",
                "type": "value_error",
            }
        )

    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    post.status = PostStatus.PUBLICADO.value
    if not post.published_at:
        post.published_at = _now()
    post.updated_at = _now()

    session.add(post)
    session.commit()
    session.refresh(post)
    background_tasks.add_task(trigger_rebuild)
    return post


@router.post("/{post_id}/unpublish", response_model=PostResponse)
def unpublish_post(
    post_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status != PostStatus.PUBLICADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo posts en estado PUBLICADO pueden devolverse a BORRADOR.",
        )

    post.status = PostStatus.BORRADOR.value
    post.updated_at = _now()
    session.add(post)
    session.commit()
    session.refresh(post)
    background_tasks.add_task(trigger_rebuild)
    return post


@router.post("/{post_id}/archive", response_model=PostResponse)
def archive_post(
    post_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status == PostStatus.ARCHIVADO.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El post ya está ARCHIVADO.")

    was_published = post.status == PostStatus.PUBLICADO.value
    post.status = PostStatus.ARCHIVADO.value
    post.updated_at = _now()
    session.add(post)
    session.commit()
    session.refresh(post)
    if was_published:
        background_tasks.add_task(trigger_rebuild)
    return post


@router.post("/{post_id}/restore", response_model=PostResponse)
def restore_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status != PostStatus.ARCHIVADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo posts en estado ARCHIVADO pueden restaurarse a BORRADOR.",
        )

    post.status = PostStatus.BORRADOR.value
    post.updated_at = _now()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status != PostStatus.BORRADOR.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solo se pueden eliminar borradores. Estado actual: {post.status}.",
        )

    session.delete(post)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

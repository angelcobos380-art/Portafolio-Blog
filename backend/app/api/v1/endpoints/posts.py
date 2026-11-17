import re
import unicodedata
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import Category, Post, get_session
from app.core.security import get_current_user
from app.schemas.post import PostCreate, PostResponse, PostStatus, PostUpdate

router = APIRouter(prefix="/posts", tags=["Posts"])


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower().strip())
    return re.sub(r"[\s-]+", "-", text).strip("-")


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post_in: PostCreate, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    if not session.get(Category, post_in.category_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Categoría especificada no existe.")

    generated_slug = slugify(post_in.title)
    if not generated_slug:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El título proporcionado no genera un slug válido.")

    if session.exec(select(Post).where(Post.slug == generated_slug)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug derivado de la publicación ya existe.")

    post = Post(
        slug=generated_slug,
        title=post_in.title,
        content=post_in.content,
        category_id=post_in.category_id,
        tags=post_in.tags or [],
        status=PostStatus.BORRADOR.value,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.get("", response_model=List[PostResponse])
def list_posts(session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    return session.exec(select(Post)).all()


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    return post


@router.put("/{post_id}", response_model=PostResponse)
def update_post(post_id: str, post_in: PostUpdate, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status == PostStatus.ARCHIVADO.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un post ARCHIVADO es inmutable y no se puede editar.")

    if post.status == PostStatus.PUBLICADO.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un post PUBLICADO no admite edición directa de contenido.")

    if post_in.category_id and post_in.category_id != post.category_id:
        if not session.get(Category, post_in.category_id):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Categoría no encontrada.")

    new_slug = post.slug
    if post_in.title and post_in.title != post.title:
        if post.published_at is None:
            new_slug = slugify(post_in.title)
            if not new_slug:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El título proporcionado no genera un slug válido.")
            if session.exec(select(Post).where(Post.slug == new_slug, Post.post_id != post_id)).first():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug derivado de la publicación ya existe.")

    if post_in.title:
        post.title = post_in.title
    post.slug = new_slug
    if post_in.content:
        post.content = post_in.content
    if post_in.category_id:
        post.category_id = post_in.category_id
    if post_in.tags is not None:
        post.tags = post_in.tags

    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.post("/{post_id}/publish", response_model=PostResponse)
def publish_post(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status not in [PostStatus.BORRADOR.value, PostStatus.DESPUBLICADO.value]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Transición no permitida desde el estado {post.status}.")

    if not post.title or not post.content or not post.slug or not post.category_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invariante violada: Campos obligatorios incompletos.")

    category = session.get(Category, post.category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La categoría asignada no existe.")

    post.frozen_category = {"id": category.category_id, "name": category.name, "slug": category.slug}
    post.status = PostStatus.PUBLICADO.value
    if not post.published_at:
        post.published_at = datetime.now(timezone.utc).isoformat()

    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.post("/{post_id}/unpublish", response_model=PostResponse)
def unpublish_post(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status != PostStatus.PUBLICADO.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo posts en estado PUBLICADO pueden ser despublicados.")

    post.status = PostStatus.DESPUBLICADO.value
    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.post("/{post_id}/archive", response_model=PostResponse)
def archive_post(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status == PostStatus.BORRADOR.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se puede archivar un post en estado BORRADOR directamente.")

    post.status = PostStatus.ARCHIVADO.value
    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")

    if post.status in [PostStatus.PUBLICADO.value, PostStatus.DESPUBLICADO.value, PostStatus.ARCHIVADO.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invariante de Dominio: Prohibición absoluta de eliminación física para posts en estado {post.status}.",
        )

    session.delete(post)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

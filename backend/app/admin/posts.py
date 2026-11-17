from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlmodel import Session, select

from app.admin.deps import get_admin_user, templates
from app.core.database import Category, Post, get_session
from app.core.utils import slugify
from app.schemas.post import PostCreate, PostStatus

router = APIRouter(prefix="/posts")


def _categories(session: Session):
    return session.exec(select(Category)).all()


def _slug_exists(session: Session, slug: str, exclude_id: str = None) -> bool:
    statement = select(Post).where(Post.slug == slug)
    if exclude_id:
        statement = statement.where(Post.post_id != exclude_id)
    return session.exec(statement).first() is not None


def _render_form(request: Request, session: Session, form: dict = None, error: str = None, action: str = "/admin/posts/new"):
    return templates.TemplateResponse(request=request, name="post_form.html", context={
        "form": form or {},
        "categories": _categories(session),
        "error": error,
        "action": action,
    })


def _form_from_post(post: Post) -> dict:
    return {
        "post_id": post.post_id,
        "title": post.title,
        "content": post.content,
        "category_id": post.category_id,
        "tags": ", ".join(post.tags or []),
    }


@router.get("")
def list_posts(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    posts = session.exec(select(Post)).all()
    return templates.TemplateResponse(request=request, name="posts_list.html", context={"posts": posts})


@router.get("/new")
def new_post(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    return _render_form(request, session)


@router.post("/new")
def create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category_id: str = Form(...),
    tags: str = Form(""),
    session: Session = Depends(get_session),
    user: dict = Depends(get_admin_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    form = {"title": title, "content": content, "category_id": category_id, "tags": tags}

    try:
        data = PostCreate(title=title, content=content, category_id=category_id, tags=tag_list)
    except ValidationError:
        return _render_form(request, session, form=form, error="Datos inválidos: título 5-120 caracteres y contenido mínimo 10.")

    if not session.get(Category, data.category_id):
        return _render_form(request, session, form=form, error="La categoría seleccionada no existe.")

    slug = slugify(data.title)
    if not slug:
        return _render_form(request, session, form=form, error="El título no genera un slug válido.")
    if _slug_exists(session, slug):
        return _render_form(request, session, form=form, error="Ya existe una publicación con ese slug.")

    post = Post(
        slug=slug,
        title=data.title,
        content=data.content,
        category_id=data.category_id,
        tags=data.tags or [],
        status=PostStatus.BORRADOR.value,
    )
    session.add(post)
    session.commit()
    return RedirectResponse("/admin/posts", status_code=303)


@router.get("/{post_id}/edit")
def edit_post_form(post_id: str, request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)
    return _render_form(request, session, form=_form_from_post(post), action=f"/admin/posts/{post_id}/edit")


@router.post("/{post_id}/edit")
def edit_post(
    post_id: str,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category_id: str = Form(...),
    tags: str = Form(""),
    session: Session = Depends(get_session),
    user: dict = Depends(get_admin_user),
):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)

    form = {"title": title, "content": content, "category_id": category_id, "tags": tags}
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if post.status == PostStatus.ARCHIVADO.value:
        return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="Un post ARCHIVADO es inmutable.")
    if post.status == PostStatus.PUBLICADO.value:
        return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="Un post PUBLICADO no se edita directamente: despublica primero.")

    try:
        PostCreate(title=title, content=content, category_id=category_id, tags=tag_list)
    except ValidationError:
        return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="Datos inválidos: título 5-120 caracteres y contenido mínimo 10.")

    if not session.get(Category, category_id):
        return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="La categoría seleccionada no existe.")

    new_slug = post.slug
    if title != post.title and post.published_at is None:
        new_slug = slugify(title)
        if not new_slug:
            return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="El título no genera un slug válido.")
        if _slug_exists(session, new_slug, exclude_id=post_id):
            return _render_form(request, session, form=form, action=f"/admin/posts/{post_id}/edit", error="Ya existe una publicación con ese slug.")

    post.title = title
    post.slug = new_slug
    post.content = content
    post.category_id = category_id
    post.tags = tag_list
    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    return RedirectResponse("/admin/posts", status_code=303)


@router.post("/{post_id}/publish")
def publish_post(post_id: str, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)

    if post.status not in [PostStatus.BORRADOR.value, PostStatus.DESPUBLICADO.value]:
        return RedirectResponse("/admin/posts", status_code=303)

    category = session.get(Category, post.category_id)
    if not category:
        return RedirectResponse("/admin/posts", status_code=303)

    post.frozen_category = {"id": category.category_id, "name": category.name, "slug": category.slug}
    post.status = PostStatus.PUBLICADO.value
    if not post.published_at:
        post.published_at = datetime.now(timezone.utc).isoformat()
    post.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(post)
    session.commit()
    return RedirectResponse("/admin/posts", status_code=303)


@router.post("/{post_id}/unpublish")
def unpublish_post(post_id: str, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)

    if post.status == PostStatus.PUBLICADO.value:
        post.status = PostStatus.DESPUBLICADO.value
        post.updated_at = datetime.now(timezone.utc).isoformat()
        session.add(post)
        session.commit()
    return RedirectResponse("/admin/posts", status_code=303)


@router.post("/{post_id}/archive")
def archive_post(post_id: str, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)

    if post.status != PostStatus.BORRADOR.value:
        post.status = PostStatus.ARCHIVADO.value
        post.updated_at = datetime.now(timezone.utc).isoformat()
        session.add(post)
        session.commit()
    return RedirectResponse("/admin/posts", status_code=303)


@router.post("/{post_id}/delete")
def delete_post(post_id: str, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    post = session.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=303)

    if post.status == PostStatus.BORRADOR.value:
        session.delete(post)
        session.commit()
    return RedirectResponse("/admin/posts", status_code=303)

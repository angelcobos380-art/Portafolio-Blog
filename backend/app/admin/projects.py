from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlmodel import Session, select

from app.admin.deps import get_admin_user, templates
from app.core.database import Project, get_session
from app.core.deploy import trigger_rebuild
from app.core.utils import slugify
from app.schemas.project import ProjectCreate, ProjectStatus

router = APIRouter(prefix="/projects")


def _slug_exists(session: Session, slug: str, exclude_id: str = None) -> bool:
    statement = select(Project).where(Project.slug == slug)
    if exclude_id:
        statement = statement.where(Project.project_id != exclude_id)
    return session.exec(statement).first() is not None


def _render_form(request: Request, form: dict = None, error: str = None, action: str = "/admin/projects/new"):
    return templates.TemplateResponse(request=request, name="project_form.html", context={
        "form": form or {},
        "error": error,
        "action": action,
    })


def _form_from_project(project: Project) -> dict:
    return {
        "project_id": project.project_id,
        "title": project.title,
        "description": project.description,
        "demo_url": project.demo_url or "",
        "cover_image_url": project.cover_image_url or "",
        "stack": ", ".join(project.stack or []),
        "is_featured": project.is_featured,
        "sort_order": project.sort_order,
    }


def _parse_project_form(title, description, demo_url, cover_image_url, stack, is_featured, sort_order):
    stack_list = [s.strip() for s in stack.split(",") if s.strip()]
    try:
        sort_order_int = int(sort_order) if sort_order else 0
    except ValueError:
        raise ValueError("sort_order")
    return ProjectCreate(
        title=title,
        description=description,
        demo_url=demo_url or None,
        cover_image_url=cover_image_url or None,
        stack=stack_list,
        is_featured=(is_featured == "true"),
        sort_order=sort_order_int,
    )


@router.get("")
def list_projects(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    projects = session.exec(select(Project)).all()
    return templates.TemplateResponse(request=request, name="projects_list.html", context={"projects": projects})


@router.get("/new")
def new_project(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    return _render_form(request)


@router.post("/new")
def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    demo_url: str = Form(""),
    cover_image_url: str = Form(""),
    stack: str = Form(""),
    is_featured: str = Form(""),
    sort_order: str = Form("0"),
    session: Session = Depends(get_session),
    user: dict = Depends(get_admin_user),
):
    form = {
        "title": title, "description": description, "demo_url": demo_url,
        "cover_image_url": cover_image_url, "stack": stack,
        "is_featured": is_featured, "sort_order": sort_order,
    }
    try:
        data = _parse_project_form(title, description, demo_url, cover_image_url, stack, is_featured, sort_order)
    except ValidationError:
        return _render_form(request, form=form, error="Datos inválidos: título mín. 3 y descripción mín. 10 caracteres.")
    except ValueError:
        return _render_form(request, form=form, error="El campo de orden debe ser un número entero.")

    slug = slugify(data.title)
    if not slug:
        return _render_form(request, form=form, error="El título no genera un slug válido.")
    if _slug_exists(session, slug):
        return _render_form(request, form=form, error="Ya existe un proyecto con ese slug.")

    project = Project(
        slug=slug,
        title=data.title,
        description=data.description,
        demo_url=data.demo_url,
        cover_image_url=data.cover_image_url,
        stack=data.stack or [],
        status=ProjectStatus.BORRADOR.value,
        is_featured=data.is_featured,
        sort_order=data.sort_order,
    )
    session.add(project)
    session.commit()
    return RedirectResponse("/admin/projects", status_code=303)


@router.get("/{project_id}/edit")
def edit_project_form(project_id: str, request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    project = session.get(Project, project_id)
    if not project:
        return RedirectResponse("/admin/projects", status_code=303)
    return _render_form(request, form=_form_from_project(project), action=f"/admin/projects/{project_id}/edit")


@router.post("/{project_id}/edit")
def edit_project(
    project_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    demo_url: str = Form(""),
    cover_image_url: str = Form(""),
    stack: str = Form(""),
    is_featured: str = Form(""),
    sort_order: str = Form("0"),
    session: Session = Depends(get_session),
    user: dict = Depends(get_admin_user),
):
    project = session.get(Project, project_id)
    if not project:
        return RedirectResponse("/admin/projects", status_code=303)

    form = {
        "title": title, "description": description, "demo_url": demo_url,
        "cover_image_url": cover_image_url, "stack": stack,
        "is_featured": is_featured, "sort_order": sort_order,
    }
    try:
        data = _parse_project_form(title, description, demo_url, cover_image_url, stack, is_featured, sort_order)
    except ValidationError:
        return _render_form(request, form=form, action=f"/admin/projects/{project_id}/edit", error="Datos inválidos: título mín. 3 y descripción mín. 10 caracteres.")
    except ValueError:
        return _render_form(request, form=form, action=f"/admin/projects/{project_id}/edit", error="El campo de orden debe ser un número entero.")

    new_slug = project.slug
    if title != project.title and project.status == ProjectStatus.BORRADOR.value:
        new_slug = slugify(title)
        if not new_slug:
            return _render_form(request, form=form, action=f"/admin/projects/{project_id}/edit", error="El título no genera un slug válido.")
        if _slug_exists(session, new_slug, exclude_id=project_id):
            return _render_form(request, form=form, action=f"/admin/projects/{project_id}/edit", error="Ya existe un proyecto con ese slug.")

    project.title = title
    project.slug = new_slug
    project.description = description
    project.demo_url = data.demo_url
    project.cover_image_url = data.cover_image_url
    project.stack = data.stack or []
    project.is_featured = data.is_featured
    project.sort_order = data.sort_order
    project.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(project)
    session.commit()
    return RedirectResponse("/admin/projects", status_code=303)


@router.post("/{project_id}/publish")
def publish_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    project = session.get(Project, project_id)
    if not project:
        return RedirectResponse("/admin/projects", status_code=303)

    if project.status == ProjectStatus.BORRADOR.value:
        project.status = ProjectStatus.PUBLICADO.value
        project.updated_at = datetime.now(timezone.utc).isoformat()
        session.add(project)
        session.commit()
        background_tasks.add_task(trigger_rebuild)
    return RedirectResponse("/admin/projects", status_code=303)


@router.post("/{project_id}/unpublish")
def unpublish_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    project = session.get(Project, project_id)
    if not project:
        return RedirectResponse("/admin/projects", status_code=303)

    if project.status == ProjectStatus.PUBLICADO.value:
        project.status = ProjectStatus.BORRADOR.value
        project.updated_at = datetime.now(timezone.utc).isoformat()
        session.add(project)
        session.commit()
        background_tasks.add_task(trigger_rebuild)
    return RedirectResponse("/admin/projects", status_code=303)


@router.post("/{project_id}/delete")
def delete_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    project = session.get(Project, project_id)
    if not project:
        return RedirectResponse("/admin/projects", status_code=303)

    session.delete(project)
    session.commit()
    background_tasks.add_task(trigger_rebuild)
    return RedirectResponse("/admin/projects", status_code=303)

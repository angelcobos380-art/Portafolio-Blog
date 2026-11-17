from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import Project, get_session
from app.core.deploy import trigger_rebuild
from app.core.security import get_current_user
from app.core.utils import slugify
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStatus, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


def _slug_exists(session: Session, slug: str, exclude_id: str = None) -> bool:
    statement = select(Project).where(Project.slug == slug)
    if exclude_id:
        statement = statement.where(Project.project_id != exclude_id)
    return session.exec(statement).first() is not None


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    generated_slug = slugify(project_in.title)
    if not generated_slug:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El título proporcionado no genera un slug válido.")

    if _slug_exists(session, generated_slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug derivado del proyecto ya existe.")

    project = Project(
        slug=generated_slug,
        title=project_in.title,
        description=project_in.description,
        demo_url=project_in.demo_url,
        cover_image_url=project_in.cover_image_url,
        stack=project_in.stack or [],
        status=ProjectStatus.BORRADOR.value,
        is_featured=project_in.is_featured,
        sort_order=project_in.sort_order,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    return session.exec(select(Project)).all()


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project_in: ProjectUpdate, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    fields = project_in.model_fields_set

    new_slug = project.slug
    if "title" in fields and project_in.title != project.title:
        if project.status == ProjectStatus.BORRADOR.value:
            new_slug = slugify(project_in.title)
            if not new_slug:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El título proporcionado no genera un slug válido.")
            if _slug_exists(session, new_slug, exclude_id=project_id):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El slug derivado del proyecto ya existe.")

    if "title" in fields:
        project.title = project_in.title
    project.slug = new_slug
    if "description" in fields:
        project.description = project_in.description
    if "demo_url" in fields:
        project.demo_url = project_in.demo_url
    if "cover_image_url" in fields:
        project.cover_image_url = project_in.cover_image_url
    if "stack" in fields:
        project.stack = project_in.stack or []
    if "is_featured" in fields:
        project.is_featured = project_in.is_featured
    if "sort_order" in fields:
        project.sort_order = project_in.sort_order

    project.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post("/{project_id}/publish", response_model=ProjectResponse)
def publish_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    if project.status != ProjectStatus.BORRADOR.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo proyectos en estado BORRADOR pueden publicarse.")

    if not project.title or not project.description or not project.slug:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invariante violada: Campos obligatorios incompletos.")

    project.status = ProjectStatus.PUBLICADO.value
    project.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(project)
    session.commit()
    session.refresh(project)
    background_tasks.add_task(trigger_rebuild)
    return project


@router.post("/{project_id}/unpublish", response_model=ProjectResponse)
def unpublish_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    if project.status != ProjectStatus.PUBLICADO.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo proyectos en estado PUBLICADO pueden despublicarse.")

    project.status = ProjectStatus.BORRADOR.value
    project.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(project)
    session.commit()
    session.refresh(project)
    background_tasks.add_task(trigger_rebuild)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    session.delete(project)
    session.commit()
    background_tasks.add_task(trigger_rebuild)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

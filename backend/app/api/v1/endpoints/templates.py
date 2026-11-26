from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.core.database import Post, Template, get_session
from app.core.security import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateStatus, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["Templates"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _name_exists(session: Session, name: str, exclude_id: Optional[str] = None) -> bool:
    for tpl in session.exec(select(Template)).all():
        if exclude_id and tpl.template_id == exclude_id:
            continue
        if tpl.name.lower() == name.strip().lower():
            return True
    return False


@router.get("", response_model=PaginatedResponse[TemplateResponse])
def list_templates(
    status_filter: Optional[str] = Query(TemplateStatus.ACTIVA.value, alias="status"),
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    templates = session.exec(select(Template)).all()

    if status_filter and status_filter.upper() != "ALL":
        allowed = {s.strip().upper() for s in status_filter.split(",") if s.strip()}
        templates = [t for t in templates if t.status in allowed]

    if q:
        needle = q.strip().lower()
        templates = [
            t
            for t in templates
            if needle in t.name.lower() or needle in (t.description or "").lower()
        ]

    templates.sort(key=lambda t: (not t.is_default, t.updated_at), reverse=False)
    # Keep default first, then newest updated_at first
    defaults = [t for t in templates if t.is_default]
    others = sorted([t for t in templates if not t.is_default], key=lambda t: t.updated_at, reverse=True)
    ordered = defaults + others

    total = len(ordered)
    start = (page - 1) * page_size
    page_items = [TemplateResponse.model_validate(t) for t in ordered[start : start + page_size]]

    return PaginatedResponse[TemplateResponse](
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    tpl_in: TemplateCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    name = tpl_in.name.strip()
    if _name_exists(session, name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una plantilla con ese nombre.")

    tpl = Template(
        name=name,
        description=tpl_in.description.strip(),
        status=TemplateStatus.ACTIVA.value,
        is_default=False,
        tokens=tpl_in.tokens.model_dump(),
    )
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
    return tpl


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    tpl_in: TemplateUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    if tpl_in.name is not None:
        name = tpl_in.name.strip()
        if _name_exists(session, name, exclude_id=template_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una plantilla con ese nombre.")
        tpl.name = name

    if tpl_in.description is not None:
        tpl.description = tpl_in.description.strip()

    if tpl_in.tokens is not None:
        tpl.tokens = tpl_in.tokens.model_dump()

    tpl.updated_at = _now()
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def duplicate_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    orig = session.get(Template, template_id)
    if not orig:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    base_name = f"{orig.name} (copia)"
    candidate = base_name[:100]
    counter = 2
    while _name_exists(session, candidate):
        suffix = f" (copia {counter})"
        candidate = f"{orig.name[: 100 - len(suffix)]}{suffix}"
        counter += 1

    copy = Template(
        name=candidate,
        description=orig.description,
        status=TemplateStatus.ACTIVA.value,
        is_default=False,
        tokens=deepcopy(orig.tokens),
    )
    session.add(copy)
    session.commit()
    session.refresh(copy)
    return copy


@router.post("/{template_id}/archive", response_model=TemplateResponse)
def archive_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    if tpl.is_default:
        tpl.is_default = False
    tpl.status = TemplateStatus.ARCHIVADA.value
    tpl.updated_at = _now()
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.post("/{template_id}/restore", response_model=TemplateResponse)
def restore_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    tpl.status = TemplateStatus.ACTIVA.value
    tpl.updated_at = _now()
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.post("/{template_id}/set-default", response_model=TemplateResponse)
def set_default_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    if tpl.status != TemplateStatus.ACTIVA.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Una plantilla ARCHIVADA no puede ser predeterminada.",
        )

    for other in session.exec(select(Template).where(Template.is_default == True)).all():  # noqa: E712
        other.is_default = False
        session.add(other)

    tpl.is_default = True
    tpl.updated_at = _now()
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")

    in_use = session.exec(select(Post).where(Post.template_id == template_id)).first()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La plantilla está en uso por al menos un post. Archívala en su lugar.",
        )

    session.delete(tpl)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlmodel import Session, select

from app.admin.deps import get_admin_user, templates
from app.core.database import Category, get_session
from app.schemas.category import CategoryCreate

router = APIRouter(prefix="/categories")


@router.get("")
def list_categories(request: Request, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    categories = session.exec(select(Category)).all()
    return templates.TemplateResponse(request=request, name="categories.html", context={"categories": categories, "error": None})


@router.post("")
def create_category(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    is_default: str = Form(""),
    session: Session = Depends(get_session),
    user: dict = Depends(get_admin_user),
):
    categories = session.exec(select(Category)).all()

    try:
        data = CategoryCreate(name=name, slug=slug, is_default=(is_default == "true"))
    except ValidationError:
        return templates.TemplateResponse(
            request=request,
            name="categories.html",
            context={"categories": categories, "error": "Datos inválidos: nombre 2-100 y slug en minúsculas con guiones."},
        )

    for cat in categories:
        if cat.name.lower() == data.name.lower() or cat.slug == data.slug:
            return templates.TemplateResponse(
                request=request,
                name="categories.html",
                context={"categories": categories, "error": "Ya existe una categoría con ese nombre o slug."},
            )

    if data.is_default:
        for cat in categories:
            cat.is_default = False
            session.add(cat)

    session.add(Category(name=data.name, slug=data.slug, is_default=data.is_default or False))
    session.commit()
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/{category_id}/delete")
def delete_category(category_id: str, session: Session = Depends(get_session), user: dict = Depends(get_admin_user)):
    category = session.get(Category, category_id)
    if not category:
        return RedirectResponse("/admin/categories", status_code=303)

    if len(session.exec(select(Category)).all()) <= 1:
        return RedirectResponse("/admin/categories", status_code=303)

    session.delete(category)
    if category.is_default:
        remaining = session.exec(select(Category)).first()
        if remaining:
            remaining.is_default = True
            session.add(remaining)

    session.commit()
    return RedirectResponse("/admin/categories", status_code=303)

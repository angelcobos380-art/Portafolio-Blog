from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import Category, get_session
from app.core.security import get_current_user
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(cat_in: CategoryCreate, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    for cat in session.exec(select(Category)).all():
        if cat.name.lower() == cat_in.name.lower() or cat.slug == cat_in.slug:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Una categoría con este nombre o slug ya existe.",
            )

    if cat_in.is_default:
        for cat in session.exec(select(Category)).all():
            cat.is_default = False
            session.add(cat)

    category = Category(name=cat_in.name, slug=cat_in.slug, is_default=cat_in.is_default or False)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.get("", response_model=List[CategoryResponse])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada.")

    if len(session.exec(select(Category)).all()) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invariante violada: Debe existir al menos una categoría en el sistema.",
        )

    session.delete(category)
    if category.is_default:
        remaining_first = session.exec(select(Category)).first()
        if remaining_first:
            remaining_first.is_default = True
            session.add(remaining_first)

    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import Media, Post, get_session
from app.core.security import get_current_user
from app.core.storage import get_storage_backend
from app.schemas.common import PaginatedResponse
from app.schemas.media import MediaResponse

router = APIRouter(prefix="/media", tags=["Media"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    alt: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de archivo no permitido. Usa JPEG, PNG, WebP o GIF.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El archivo está vacío.")

    if len(data) > settings.MEDIA_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el límite de {settings.MEDIA_MAX_BYTES} bytes.",
        )

    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()
        with Image.open(BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no es una imagen válida o está corrupto.",
        )

    storage = get_storage_backend()
    stored = storage.save(data, content_type)

    media = Media(
        url=stored.url,
        storage_key=stored.storage_key,
        mime=content_type,
        size=len(data),
        width=width,
        height=height,
        alt=alt.strip()[:200] if alt else None,
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    return media


@router.get("", response_model=PaginatedResponse[MediaResponse])
def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    items = sorted(session.exec(select(Media)).all(), key=lambda m: m.created_at, reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    page_items = [MediaResponse.model_validate(m) for m in items[start : start + page_size]]
    return PaginatedResponse[MediaResponse](
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    media = session.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado.")

    for post in session.exec(select(Post)).all():
        if post.cover_image_url == media.url or (post.content_html and media.url in post.content_html):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El archivo está referenciado en uno o más posts.",
            )

    storage = get_storage_backend()
    storage.delete(media.storage_key)

    session.delete(media)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

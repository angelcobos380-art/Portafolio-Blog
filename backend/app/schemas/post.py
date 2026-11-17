from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PostStatus(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    DESPUBLICADO = "DESPUBLICADO"
    ARCHIVADO = "ARCHIVADO"


class PostBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=120, example="Novedades en FastAPI")
    content: str = Field(..., min_length=10, example="# Introducción\nFastAPI es...")
    category_id: str = Field(..., example="0192a3b5-1122-7334-8445-556677889900")
    tags: Optional[List[str]] = Field(default_factory=list, max_length=10, example=["python", "fastapi"])


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=120)
    content: Optional[str] = Field(None, min_length=10)
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None


class PostResponse(BaseModel):
    post_id: str
    slug: str
    title: str
    content: str
    status: PostStatus
    category_id: str
    frozen_category: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    published_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

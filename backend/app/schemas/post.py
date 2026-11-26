from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.template import TemplateSummary


class PostStatus(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    ARCHIVADO = "ARCHIVADO"


class SeoMeta(BaseModel):
    title: Optional[str] = Field(None, max_length=160)
    description: Optional[str] = Field(None, max_length=320)
    og_image: Optional[str] = Field(None, max_length=500)


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    slug: Optional[str] = Field(None, max_length=140)
    tags: List[str] = Field(default_factory=list, max_length=10)
    template_id: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=300)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    seo: Optional[SeoMeta] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None
    content: Optional[str] = None
    content_schema_version: Optional[int] = Field(None, ge=1)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    slug: Optional[str] = Field(None, max_length=140)
    tags: Optional[List[str]] = Field(None, max_length=10)
    template_id: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=300)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    seo: Optional[SeoMeta] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None
    content: Optional[str] = None
    content_schema_version: Optional[int] = Field(None, ge=1)


class PostListItem(BaseModel):
    post_id: str
    slug: str
    title: str
    status: PostStatus
    tags: List[str] = Field(default_factory=list)
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    template_id: Optional[str] = None
    created_at: str
    updated_at: str
    published_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PostResponse(BaseModel):
    post_id: str
    slug: str
    title: str
    status: PostStatus
    tags: List[str] = Field(default_factory=list)
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    seo: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None
    content: Optional[str] = None
    content_schema_version: Optional[int] = None
    created_at: str
    updated_at: str
    published_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PublicPostListItem(BaseModel):
    post_id: str
    slug: str
    title: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    published_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PublicPostDetail(BaseModel):
    post_id: str
    slug: str
    title: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    seo: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    published_at: Optional[str] = None
    content_html: Optional[str] = None
    content: Optional[str] = None
    template: Optional[TemplateSummary] = None

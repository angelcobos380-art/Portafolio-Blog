from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=10)
    demo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    stack: List[str] = Field(default_factory=list)
    is_featured: bool = False
    sort_order: int = 0


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=120)
    description: Optional[str] = Field(None, min_length=10)
    demo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    stack: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


class ProjectResponse(BaseModel):
    project_id: str
    slug: str
    title: str
    description: str
    demo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    stack: List[str] = Field(default_factory=list)
    status: ProjectStatus
    is_featured: bool
    sort_order: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

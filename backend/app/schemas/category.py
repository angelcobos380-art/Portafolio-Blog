from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Tecnología")
    slug: str = Field(..., pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", example="tecnologia")
    is_default: Optional[bool] = Field(default=False)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    category_id: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

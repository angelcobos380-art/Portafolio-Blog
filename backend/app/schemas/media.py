from typing import Optional

from pydantic import BaseModel, ConfigDict


class MediaResponse(BaseModel):
    media_id: str
    url: str
    mime: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

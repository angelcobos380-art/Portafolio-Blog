from typing import List, Optional

from pydantic import BaseModel


class PostMetricsItem(BaseModel):
    post_id: str
    slug: str
    title: str
    views: int
    last_viewed_at: Optional[str] = None


class ProjectMetricsItem(BaseModel):
    project_id: str
    slug: str
    title: str
    views: int
    last_viewed_at: Optional[str] = None


class MetricsOverview(BaseModel):
    total_post_views: int
    total_project_views: int
    posts: List[PostMetricsItem]
    projects: List[ProjectMetricsItem]

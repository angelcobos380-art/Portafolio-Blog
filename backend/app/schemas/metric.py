from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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


class SummaryTotals(BaseModel):
    posts: int
    by_status: Dict[str, int]
    views: int


class TopTagItem(BaseModel):
    tag: str
    count: int


class PostsPerMonthItem(BaseModel):
    month: str
    created: int
    published: int


class TopPostItem(BaseModel):
    post_id: str
    slug: str
    title: str
    views: int


class MetricsSummaryResponse(BaseModel):
    totals: SummaryTotals
    top_tags: List[TopTagItem]
    posts_per_month: List[PostsPerMonthItem]
    top_posts: List[TopPostItem]


class ViewsSeriesPoint(BaseModel):
    date: str
    views: int


class ViewsSeriesResponse(BaseModel):
    from_date: str = Field(..., serialization_alias="from")
    to_date: str = Field(..., serialization_alias="to")
    granularity: Literal["day", "week"]
    series: List[ViewsSeriesPoint]

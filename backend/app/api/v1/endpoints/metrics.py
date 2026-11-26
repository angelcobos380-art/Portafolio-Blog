from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.core.database import Post, PostView, PostViewDaily, Project, ProjectView, get_session
from app.core.security import get_current_user
from app.schemas.metric import (
    MetricsOverview,
    MetricsSummaryResponse,
    PostMetricsItem,
    PostsPerMonthItem,
    ProjectMetricsItem,
    SummaryTotals,
    TopPostItem,
    TopTagItem,
    ViewsSeriesPoint,
    ViewsSeriesResponse,
)
from app.schemas.post import PostStatus
from app.schemas.project import ProjectStatus

router = APIRouter(tags=["Metrics"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


@router.post("/public/posts/{slug}/view", status_code=status.HTTP_204_NO_CONTENT)
def record_post_view(slug: str, session: Session = Depends(get_session)):
    post = session.exec(
        select(Post).where(Post.slug == slug, Post.status == PostStatus.PUBLICADO.value)
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada.")

    view = session.get(PostView, post.post_id)
    if view is None:
        view = PostView(post_id=post.post_id, count=1)
    else:
        view.count += 1
    view.last_viewed_at = _now()
    session.add(view)

    today_str = _today_utc().isoformat()
    daily = session.get(PostViewDaily, (post.post_id, today_str))
    if daily is None:
        daily = PostViewDaily(post_id=post.post_id, date=today_str, count=1)
    else:
        daily.count += 1
    session.add(daily)

    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/public/projects/{slug}/view", status_code=status.HTTP_204_NO_CONTENT)
def record_project_view(slug: str, session: Session = Depends(get_session)):
    project = session.exec(
        select(Project).where(Project.slug == slug, Project.status == ProjectStatus.PUBLICADO.value)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")

    view = session.get(ProjectView, project.project_id)
    if view is None:
        view = ProjectView(project_id=project.project_id, count=1)
    else:
        view.count += 1
    view.last_viewed_at = _now()
    session.add(view)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/metrics/overview", response_model=MetricsOverview)
def metrics_overview(session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    posts = session.exec(select(Post)).all()
    projects = session.exec(select(Project)).all()
    post_views_map = {v.post_id: v for v in session.exec(select(PostView)).all()}
    project_views_map = {v.project_id: v for v in session.exec(select(ProjectView)).all()}

    post_items = []
    total_post_views = 0
    for post in posts:
        view = post_views_map.get(post.post_id)
        views = view.count if view else 0
        total_post_views += views
        post_items.append(
            PostMetricsItem(
                post_id=post.post_id,
                slug=post.slug,
                title=post.title,
                views=views,
                last_viewed_at=view.last_viewed_at if view else None,
            )
        )

    project_items = []
    total_project_views = 0
    for project in projects:
        view = project_views_map.get(project.project_id)
        views = view.count if view else 0
        total_project_views += views
        project_items.append(
            ProjectMetricsItem(
                project_id=project.project_id,
                slug=project.slug,
                title=project.title,
                views=views,
                last_viewed_at=view.last_viewed_at if view else None,
            )
        )

    return MetricsOverview(
        total_post_views=total_post_views,
        total_project_views=total_project_views,
        posts=post_items,
        projects=project_items,
    )


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
def metrics_summary(
    months: int = Query(12, ge=1, le=36),
    top: int = Query(5, ge=1, le=20),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    posts = session.exec(select(Post)).all()
    post_views_map = {v.post_id: v.count for v in session.exec(select(PostView)).all()}

    by_status = {s.value: 0 for s in PostStatus}
    tag_counter: Counter = Counter()
    created_per_month: defaultdict[str, int] = defaultdict(int)
    published_per_month: defaultdict[str, int] = defaultdict(int)

    for post in posts:
        if post.status in by_status:
            by_status[post.status] += 1
        else:
            by_status[post.status] = by_status.get(post.status, 0) + 1

        for tag in post.tags or []:
            tag_counter[tag] += 1

        if post.created_at and len(post.created_at) >= 7:
            created_per_month[post.created_at[:7]] += 1
        if post.published_at and len(post.published_at) >= 7:
            published_per_month[post.published_at[:7]] += 1

    today = _today_utc()
    month_keys = []
    year, month = today.year, today.month
    for _ in range(months):
        month_keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    month_keys.reverse()

    posts_per_month = [
        PostsPerMonthItem(
            month=m,
            created=created_per_month[m],
            published=published_per_month[m],
        )
        for m in month_keys
    ]

    top_tags = [TopTagItem(tag=t, count=c) for t, c in tag_counter.most_common(top)]

    posts_with_views = sorted(
        posts,
        key=lambda p: post_views_map.get(p.post_id, 0),
        reverse=True,
    )
    top_posts = [
        TopPostItem(
            post_id=p.post_id,
            slug=p.slug,
            title=p.title,
            views=post_views_map.get(p.post_id, 0),
        )
        for p in posts_with_views[:top]
    ]

    return MetricsSummaryResponse(
        totals=SummaryTotals(
            posts=len(posts),
            by_status=by_status,
            views=sum(post_views_map.values()),
        ),
        top_tags=top_tags,
        posts_per_month=posts_per_month,
        top_posts=top_posts,
    )


@router.get("/metrics/views", response_model=ViewsSeriesResponse)
def metrics_views(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    granularity: Literal["day", "week"] = "day",
    post_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    today = _today_utc()
    try:
        end = date.fromisoformat(to_date) if to_date else today
        start = date.fromisoformat(from_date) if from_date else (end - timedelta(days=29))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Las fechas deben tener formato YYYY-MM-DD.",
        )

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El parámetro 'from' no puede ser posterior a 'to'.",
        )
    if (end - start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El rango máximo permitido es de 366 días.",
        )

    stmt = select(PostViewDaily).where(
        PostViewDaily.date >= start.isoformat(),
        PostViewDaily.date <= end.isoformat(),
    )
    if post_id:
        stmt = stmt.where(PostViewDaily.post_id == post_id)

    rows = session.exec(stmt).all()
    daily_totals: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        daily_totals[row.date] += row.count

    series = []
    if granularity == "day":
        cursor = start
        while cursor <= end:
            key = cursor.isoformat()
            series.append(ViewsSeriesPoint(date=key, views=daily_totals[key]))
            cursor += timedelta(days=1)
    else:
        weekly_totals: defaultdict[str, int] = defaultdict(int)
        cursor = start
        while cursor <= end:
            week_start = cursor - timedelta(days=cursor.weekday())
            bucket = max(week_start, start).isoformat()
            weekly_totals[bucket] += daily_totals[cursor.isoformat()]
            cursor += timedelta(days=1)
        for bucket in sorted(weekly_totals.keys()):
            series.append(ViewsSeriesPoint(date=bucket, views=weekly_totals[bucket]))

    return ViewsSeriesResponse(
        from_date=start.isoformat(),
        to_date=end.isoformat(),
        granularity=granularity,
        series=series,
    )


@router.get("/metrics/posts/{post_id}", response_model=PostMetricsItem)
def post_metrics(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado.")
    view = session.get(PostView, post_id)
    return PostMetricsItem(
        post_id=post.post_id,
        slug=post.slug,
        title=post.title,
        views=view.count if view else 0,
        last_viewed_at=view.last_viewed_at if view else None,
    )


@router.get("/metrics/projects/{project_id}", response_model=ProjectMetricsItem)
def project_metrics(
    project_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado.")
    view = session.get(ProjectView, project_id)
    return ProjectMetricsItem(
        project_id=project.project_id,
        slug=project.slug,
        title=project.title,
        views=view.count if view else 0,
        last_viewed_at=view.last_viewed_at if view else None,
    )

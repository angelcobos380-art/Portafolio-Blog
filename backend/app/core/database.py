from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, Session, SQLModel, create_engine, select
from uuid6 import uuid7

from app.core.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid7())


DEFAULT_PORTFOLIO_TOKENS: Dict[str, Any] = {
    "version": 1,
    "colors": {
        "accent": "#e34b4e",
        "background": "#0b0a0b",
        "surface": "#1c191b",
        "text": "#f7f3f1",
        "textMuted": "#b6adab",
        "border": "#2e292b",
        "link": "#e34b4e",
        "codeBg": "#070607",
    },
    "typography": {
        "headingFont": "Inter, ui-sans-serif, system-ui, sans-serif",
        "bodyFont": "Inter, ui-sans-serif, system-ui, sans-serif",
        "codeFont": "ui-monospace, SFMono-Regular, Menlo, monospace",
        "baseSize": 17,
        "lineHeight": 1.8,
    },
    "layout": {
        "maxWidth": 780,
        "density": "comfortable",
        "headerStyle": "minimal",
        "imageRadius": 12,
        "shadow": "soft",
    },
    "blocks": {
        "callout": {
            "info": {"bg": "#172536", "border": "#38bdf8"},
            "tip": {"bg": "#14291f", "border": "#22c55e"},
            "warning": {"bg": "#2e2412", "border": "#eab308"},
            "danger": {"bg": "#311619", "border": "#e34b4e"},
        },
        "quote": {"borderColor": "#e34b4e", "style": "italic"},
        "code": {"radius": 12, "showLanguageBadge": True},
    },
}


class User(SQLModel, table=True):
    user_id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = "ADMIN"
    is_active: bool = True
    created_at: str = Field(default_factory=now_iso)


class Category(SQLModel, table=True):
    """Tabla heredada conservada para compatibilidad de BD; sin uso en CMS v1.3."""

    category_id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    is_default: bool = False
    created_at: str = Field(default_factory=now_iso)


class Template(SQLModel, table=True):
    __tablename__ = "templates"

    template_id: str = Field(default_factory=new_id, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    description: str = Field(default="", max_length=300)
    status: str = Field(default="ACTIVA", max_length=20)
    is_default: bool = False
    tokens: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Post(SQLModel, table=True):
    post_id: str = Field(default_factory=new_id, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    content: Optional[str] = Field(default=None)
    content_json: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    content_html: Optional[str] = Field(default=None, sa_column=Column(Text))
    content_schema_version: Optional[int] = None
    excerpt: Optional[str] = Field(default=None, max_length=300)
    cover_image_url: Optional[str] = Field(default=None, max_length=500)
    seo: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    template_id: Optional[str] = Field(default=None, foreign_key="templates.template_id")
    category_id: Optional[str] = None
    frozen_category: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str
    published_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Media(SQLModel, table=True):
    __tablename__ = "media"

    media_id: str = Field(default_factory=new_id, primary_key=True)
    url: str = Field(max_length=500)
    storage_key: str = Field(max_length=300)
    mime: str = Field(max_length=50)
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = Field(default=None, max_length=200)
    created_at: str = Field(default_factory=now_iso)


class LoginAttempt(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True)
    success: bool
    attempted_at: str = Field(default_factory=now_iso)


class Project(SQLModel, table=True):
    project_id: str = Field(default_factory=new_id, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    description: str
    demo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    stack: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str
    is_featured: bool = False
    sort_order: int = 0
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class PostView(SQLModel, table=True):
    __tablename__ = "post_views"

    post_id: str = Field(primary_key=True)
    count: int = 0
    last_viewed_at: Optional[str] = None


class PostViewDaily(SQLModel, table=True):
    __tablename__ = "post_view_daily"

    post_id: str = Field(primary_key=True)
    date: str = Field(primary_key=True, max_length=10)
    count: int = 0


class ProjectView(SQLModel, table=True):
    __tablename__ = "project_views"

    project_id: str = Field(primary_key=True)
    count: int = 0
    last_viewed_at: Optional[str] = None


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def seed_admin() -> None:
    from app.core.security import get_password_hash

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == settings.ADMIN_EMAIL)).first()
        if existing is None:
            session.add(
                User(
                    email=settings.ADMIN_EMAIL,
                    password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                )
            )
            session.commit()


def seed_default_template() -> None:
    with Session(engine) as session:
        existing = session.exec(select(Template)).first()
        if existing is None:
            session.add(
                Template(
                    name="Oscuro Editorial (Predeterminada)",
                    description="Estilo oscuro minimalista basado en el portafolio principal.",
                    status="ACTIVA",
                    is_default=True,
                    tokens=DEFAULT_PORTFOLIO_TOKENS,
                )
            )
            session.commit()

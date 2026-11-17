from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, create_engine, select
from uuid6 import uuid7

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid7())


class User(SQLModel, table=True):
    user_id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = "ADMIN"
    is_active: bool = True
    created_at: str = Field(default_factory=now_iso)


class Category(SQLModel, table=True):
    category_id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    is_default: bool = False
    created_at: str = Field(default_factory=now_iso)


class Post(SQLModel, table=True):
    post_id: str = Field(default_factory=new_id, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    content: str
    category_id: str
    frozen_category: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str
    published_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


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
            session.add(User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            ))
            session.commit()

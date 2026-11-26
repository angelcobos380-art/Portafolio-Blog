"""Initial schema (pre-Alembic baseline)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-25 19:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "category",
        sa.Column("category_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_category_slug", "category", ["slug"], unique=True)

    op.create_table(
        "post",
        sa.Column("post_id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("frozen_category", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("published_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_post_slug", "post", ["slug"], unique=True)

    op.create_table(
        "loginattempt",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.String(), nullable=False),
    )
    op.create_index("ix_loginattempt_email", "loginattempt", ["email"], unique=False)

    op.create_table(
        "project",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("demo_url", sa.String(), nullable=True),
        sa.Column("cover_image_url", sa.String(), nullable=True),
        sa.Column("stack", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_project_slug", "project", ["slug"], unique=True)

    op.create_table(
        "post_views",
        sa.Column("post_id", sa.String(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("last_viewed_at", sa.String(), nullable=True),
    )

    op.create_table(
        "project_views",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("last_viewed_at", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("project_views")
    op.drop_table("post_views")
    op.drop_index("ix_project_slug", table_name="project")
    op.drop_table("project")
    op.drop_index("ix_loginattempt_email", table_name="loginattempt")
    op.drop_table("loginattempt")
    op.drop_index("ix_post_slug", table_name="post")
    op.drop_table("post")
    op.drop_index("ix_category_slug", table_name="category")
    op.drop_table("category")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")

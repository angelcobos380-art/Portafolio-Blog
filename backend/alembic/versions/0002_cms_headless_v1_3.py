"""CMS headless v1.3: templates, media, post_view_daily, rich post fields

Revision ID: 0002_cms_headless_v1_3
Revises: 0001_initial_schema
Create Date: 2026-11-25 19:35:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_cms_headless_v1_3"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("template_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVA"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tokens", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_templates_name", "templates", ["name"], unique=True)

    op.create_table(
        "media",
        sa.Column("media_id", sa.String(), primary_key=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.String(length=300), nullable=False),
        sa.Column("mime", sa.String(length=50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("alt", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )

    op.create_table(
        "post_view_daily",
        sa.Column("post_id", sa.String(), primary_key=True),
        sa.Column("date", sa.String(length=10), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )

    with op.batch_alter_table("post") as batch_op:
        batch_op.alter_column("content", existing_type=sa.String(), nullable=True)
        batch_op.alter_column("category_id", existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column("content_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("content_html", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("content_schema_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("excerpt", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("cover_image_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("seo", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_post_template_id",
            "templates",
            ["template_id"],
            ["template_id"],
        )

    # Normaliza posts legados en estado DESPUBLICADO al modelo de 3 estados (BORRADOR)
    op.execute(sa.text("UPDATE post SET status = 'BORRADOR' WHERE status = 'DESPUBLICADO'"))


def downgrade() -> None:
    with op.batch_alter_table("post") as batch_op:
        batch_op.drop_constraint("fk_post_template_id", type_="foreignkey")
        batch_op.drop_column("template_id")
        batch_op.drop_column("seo")
        batch_op.drop_column("cover_image_url")
        batch_op.drop_column("excerpt")
        batch_op.drop_column("content_schema_version")
        batch_op.drop_column("content_html")
        batch_op.drop_column("content_json")
        batch_op.alter_column("category_id", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("content", existing_type=sa.String(), nullable=False)

    op.drop_table("post_view_daily")
    op.drop_table("media")
    op.drop_index("ix_templates_name", table_name="templates")
    op.drop_table("templates")

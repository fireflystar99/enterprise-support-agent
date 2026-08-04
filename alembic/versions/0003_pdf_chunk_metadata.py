"""add pdf chunk metadata

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("source_type", sa.String(20), nullable=False, server_default="markdown"))
    op.add_column("chunks", sa.Column("source_path", sa.String(512), nullable=False, server_default=""))
    op.add_column("chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("content_type", sa.String(20), nullable=False, server_default="text"))
    op.add_column("chunks", sa.Column("table_name", sa.String(255), nullable=True))
    op.add_column("chunks", sa.Column("table_json", sa.Text(), nullable=True))
    op.create_index("ix_chunks_source_type", "chunks", ["source_type"])
    op.create_index("ix_chunks_page_number", "chunks", ["page_number"])


def downgrade() -> None:
    op.drop_index("ix_chunks_page_number", table_name="chunks")
    op.drop_index("ix_chunks_source_type", table_name="chunks")
    op.drop_column("chunks", "table_json")
    op.drop_column("chunks", "table_name")
    op.drop_column("chunks", "content_type")
    op.drop_column("chunks", "page_number")
    op.drop_column("chunks", "source_path")
    op.drop_column("chunks", "source_type")

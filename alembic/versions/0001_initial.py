"""initial

Revision ID: 0001
Revises:
Create Date: 2026-07-28

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100), default="General"),
        sa.Column("version", sa.String(20), default="1.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("section", sa.String(255), default=""),
        sa.Column("department", sa.String(100), default="General"),
        sa.Column("access_level", sa.String(20), default="public"),
        sa.Column("version", sa.String(20), default="1.0"),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), default=""),
        sa.Column("risk_level", sa.String(20), default="low"),
        sa.Column("status", sa.String(20), default="open"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "query_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("retrieved_chunk_ids", sa.Text(), default=""),
        sa.Column("answer", sa.Text(), default=""),
        sa.Column("route", sa.String(20), nullable=False),
        sa.Column("confidence", sa.String(10), default="low"),
        sa.Column("ticket_id", sa.String(36), nullable=True),
        sa.Column("latency_ms", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("query_traces")
    op.drop_table("tickets")
    op.drop_table("chunks")
    op.drop_table("documents")

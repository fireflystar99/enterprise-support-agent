"""add retrieval indexes

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.create_index("ix_chunks_department", "chunks", ["department"])


def downgrade() -> None:
    op.drop_index("ix_chunks_department", table_name="chunks")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="General")
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    chunks = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str] = mapped_column(String(255), default="")
    department: Mapped[str] = mapped_column(String(100), default="General")
    access_level: Mapped[str] = mapped_column(String(20), default="public")
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    embedding: Mapped[Vector] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    document = relationship("Document", back_populates="chunks")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class QueryTrace(Base):
    __tablename__ = "query_traces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    route: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), default="low")
    ticket_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

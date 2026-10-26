"""Database tables. Every change here needs an Alembic migration (see guide.md)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

Json = JSON().with_variant(JSONB(), "postgresql")


def now() -> datetime:
    return datetime.now(UTC)


class StoredFile(Base):
    """A file kept in storage. The bytes live on disk under their SHA-256; this row is the record."""

    __tablename__ = "stored_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_name: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(
        String(50), default="upload"
    )  # upload | output | connector key
    actor: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RuleSet(Base):
    """One version of a workflow's rules. Saving rules always adds a new version."""

    __tablename__ = "rule_sets"
    __table_args__ = (UniqueConstraint("workflow_key", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_key: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer)
    values: Mapped[dict] = mapped_column(Json, default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Run(Base):
    """One execution of a workflow: what went in, which rules, what came out, who and when."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_key: Mapped[str] = mapped_column(String(100), index=True)
    workflow_version: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default="queued"
    )  # queued|running|succeeded|failed
    params: Mapped[dict] = mapped_column(Json, default=dict)
    rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("rule_sets.id"))
    result: Mapped[dict | None] = mapped_column(Json)
    error: Mapped[str | None] = mapped_column(Text)
    trigger: Mapped[str] = mapped_column(String(50), default="manual")  # manual | schedule | api
    actor: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rule_set: Mapped[RuleSet | None] = relationship()
    files: Mapped[list["RunFile"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunFile.id"
    )


class RunFile(Base):
    """Links a run to its input and output files."""

    __tablename__ = "run_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stored_files.id"))
    role: Mapped[str] = mapped_column(String(10))  # input | output
    slot: Mapped[str] = mapped_column(String(100))

    run: Mapped[Run] = relationship(back_populates="files")
    file: Mapped[StoredFile] = relationship()


class Connection(Base):
    """Settings for an outside system (Zoho, PACT, a mailbox...). Secrets are stored encrypted."""

    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(50))  # matches a connector kind in app/connectors
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict] = mapped_column(Json, default=dict)
    secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AuditEvent(Base):
    """Append-only log of everything that happens. Rows are never updated or deleted."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[dict] = mapped_column(Json, default=dict)

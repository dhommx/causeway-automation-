"""data folder: file paths, run folders, portal settings

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 09:00:00

Files used to be kept under their SHA-256 in backend/storage/<sha[:2]>/<sha>. Rows from then get
that path, so older runs still open; new files go to the readable data folder.
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_STORAGE = str(Path(__file__).resolve().parents[2] / "storage")


def upgrade() -> None:
    op.add_column("stored_files", sa.Column("path", sa.String(length=1000), nullable=True))
    op.execute(
        sa.text(
            "UPDATE stored_files SET path = :root || '/' || substr(sha256, 1, 2) || '/' || sha256"
        ).bindparams(root=LEGACY_STORAGE)
    )
    op.alter_column("stored_files", "path", nullable=False)
    op.add_column("runs", sa.Column("folder", sa.String(length=1000), nullable=True))
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column(
            "value",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_column("runs", "folder")
    op.drop_column("stored_files", "path")

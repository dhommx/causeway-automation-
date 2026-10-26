"""Job queue tables (Procrastinate's own schema).

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""

from procrastinate.schema import SchemaManager

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Run through the raw driver cursor with no parameters, so the % signs in the SQL stay as is.
    cursor = op.get_bind().connection.dbapi_connection.cursor()
    cursor.execute(SchemaManager.get_schema())


def downgrade() -> None:
    # The queue objects live in the public schema with a procrastinate_ prefix; drop them by hand
    # if this is ever needed. Not done automatically to avoid losing queued jobs by accident.
    pass

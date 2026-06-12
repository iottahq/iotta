"""scoped tokens

Replaces the single encrypted group token with a fine-grained token system.
Each group can have multiple tokens, each scoped to specific devices and actions.

- Creates tokens table
- Creates token_devices table
- Drops groups.token column (existing group tokens are invalidated — re-create via UI)

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "tokens" not in tables:
        op.create_table(
            "tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column(
                "group_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("groups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_tokens_token_hash", "tokens", ["token_hash"], unique=True)
        op.create_index("ix_tokens_group_id", "tokens", ["group_id"])

    if "token_devices" not in tables:
        op.create_table(
            "token_devices",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "token_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tokens.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "device_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("devices.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("allowed_actions", postgresql.JSON(), nullable=False),
        )
        op.create_index("ix_token_devices_token_id", "token_devices", ["token_id"])
        op.create_unique_constraint("uq_token_device", "token_devices", ["token_id", "device_id"])

    # Drop the old encrypted token column from groups
    group_columns = [c["name"] for c in inspector.get_columns("groups")]
    if "token" in group_columns:
        op.drop_column("groups", "token")


def downgrade() -> None:
    op.drop_table("token_devices")
    op.drop_table("tokens")
    op.add_column("groups", sa.Column("token", sa.String(), nullable=True))

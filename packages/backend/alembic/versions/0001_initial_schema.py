"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create groups table if it doesn't exist yet
    if "groups" not in tables:
        op.create_table(
            "groups",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # Create credentials table if it doesn't exist yet
    if "credentials" not in tables:
        op.create_table(
            "credentials",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("data", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # Create devices table if it doesn't exist yet
    if "devices" not in tables:
        op.create_table(
            "devices",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("plugin_id", sa.String(), nullable=False),
            sa.Column(
                "credential_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("credentials.id"),
                nullable=False,
            ),
            sa.Column(
                "group_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("groups.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    else:
        # devices table already exists – add group_id if missing
        device_columns = [c["name"] for c in inspector.get_columns("devices")]
        if "group_id" not in device_columns:
            op.add_column(
                "devices",
                sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
            )
            op.create_foreign_key(
                "fk_devices_group_id",
                "devices",
                "groups",
                ["group_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # Change credentials.data from JSON to String if still JSON
    # (only relevant when upgrading an existing DB)
    inspector2 = sa.inspect(conn)
    if "credentials" in inspector2.get_table_names():
        cred_columns = {c["name"]: c for c in inspector2.get_columns("credentials")}
        if "data" in cred_columns:
            col_type = cred_columns["data"]["type"]
            if not isinstance(col_type, sa.String):
                op.alter_column(
                    "credentials",
                    "data",
                    type_=sa.String(),
                    existing_type=col_type,
                    postgresql_using="data::text",
                    nullable=False,
                )


def downgrade() -> None:
    op.drop_table("devices")
    op.drop_table("credentials")
    op.drop_table("groups")

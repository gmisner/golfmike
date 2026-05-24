"""Add watchlist table

Revision ID: 005
Revises: 004
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "watchlist",
        sa.Column("id",          sa.Integer,     primary_key=True),
        sa.Column("user_id",     sa.Integer,     sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aircraft_id", sa.String(20),  nullable=False),   # tail / callsign e.g. N123AB or DAL123
        sa.Column("label",       sa.String(100), nullable=True),    # optional friendly name
        sa.Column("notify_departure", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notify_arrival",   sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notify_filed",     sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_watchlist_user_id",     "watchlist", ["user_id"])
    op.create_index("ix_watchlist_aircraft_id", "watchlist", ["aircraft_id"])
    # Prevent duplicate entries per user
    op.create_index(
        "uq_watchlist_user_aircraft",
        "watchlist",
        ["user_id", "aircraft_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_watchlist_user_aircraft", table_name="watchlist")
    op.drop_index("ix_watchlist_aircraft_id",   table_name="watchlist")
    op.drop_index("ix_watchlist_user_id",        table_name="watchlist")
    op.drop_table("watchlist")

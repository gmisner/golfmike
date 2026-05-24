"""Add push_subscriptions, notification_log, and user_notification_channels

Revision ID: 006
Revises: 005
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Browser push subscriptions (one per browser/device per user)
    op.create_table(
        "push_subscriptions",
        sa.Column("id",         sa.Integer,    primary_key=True),
        sa.Column("user_id",    sa.Integer,    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint",   sa.Text,       nullable=False),
        sa.Column("p256dh",     sa.Text,       nullable=False),
        sa.Column("auth",       sa.Text,       nullable=False),
        sa.Column("user_agent", sa.Text,       nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)

    # Apprise notification channels per user (ntfy, Telegram, SMS, etc.)
    op.create_table(
        "notification_channels",
        sa.Column("id",         sa.Integer,    primary_key=True),
        sa.Column("user_id",    sa.Integer,    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label",      sa.String(80), nullable=False),   # e.g. "My Phone", "Telegram"
        sa.Column("apprise_url",sa.Text,       nullable=False),   # e.g. tgram://bottoken/chatid
        sa.Column("enabled",    sa.Boolean,    nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_notification_channels_user_id", "notification_channels", ["user_id"])

    # Log of sent notifications to prevent duplicates
    op.create_table(
        "notification_log",
        sa.Column("id",           sa.Integer,    primary_key=True),
        sa.Column("user_id",      sa.Integer,    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aircraft_id",  sa.String(20), nullable=False),
        sa.Column("event_type",   sa.String(30), nullable=False),  # departed, arrived, filed
        sa.Column("event_key",    sa.String(100),nullable=False),  # dedup key (aircraft+type+gufi/date)
        sa.Column("sent_at",      sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_notification_log_user_aircraft", "notification_log",
                    ["user_id", "aircraft_id"])
    op.create_index("ix_notification_log_event_key", "notification_log",
                    ["user_id", "event_key"], unique=True)


def downgrade():
    op.drop_index("ix_notification_log_event_key",      table_name="notification_log")
    op.drop_index("ix_notification_log_user_aircraft",  table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("ix_notification_channels_user_id",   table_name="notification_channels")
    op.drop_table("notification_channels")
    op.drop_index("ix_push_subscriptions_endpoint",     table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id",      table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

"""Add users table for auth

Revision ID: 004
Revises: 003
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id",           sa.Integer,     primary_key=True),
        sa.Column("email",        sa.String(255),  nullable=False),
        sa.Column("password_hash",sa.String(255),  nullable=False),
        sa.Column("display_name", sa.String(100),  nullable=True),
        sa.Column("is_active",    sa.Boolean,      nullable=False, server_default="true"),
        sa.Column("is_admin",     sa.Boolean,      nullable=False, server_default="false"),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_login",   sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Token denylist for logout / refresh revocation
    op.create_table(
        "jwt_denylist",
        sa.Column("id",         sa.Integer,  primary_key=True),
        sa.Column("jti",        sa.String(64), nullable=False),
        sa.Column("token_type", sa.String(16), nullable=False),   # "access" | "refresh"
        sa.Column("revoked_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_jwt_denylist_jti", "jwt_denylist", ["jti"], unique=True)


def downgrade():
    op.drop_index("ix_jwt_denylist_jti", table_name="jwt_denylist")
    op.drop_table("jwt_denylist")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

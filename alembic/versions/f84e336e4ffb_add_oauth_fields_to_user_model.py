"""Create users table with OAuth support

Revision ID: f84e336e4ffb
Revises:
Create Date: 2025-09-23 17:09:10.155034
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f84e336e4ffb"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create users table including OAuth columns."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("oauth_provider", sa.String(length=50), nullable=True),
        sa.Column("oauth_id", sa.String(length=255), nullable=True),
        sa.Column("oauth_email_verified", sa.Boolean(), nullable=True),
        sa.Column("oauth_refresh_token", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )

    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)


def downgrade() -> None:
    """Drop users table and indexes."""
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

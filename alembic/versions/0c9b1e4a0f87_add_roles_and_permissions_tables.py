"""Add role and permission tables for RBAC scaffolding."""

from collections.abc import Mapping, Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0c9b1e4a0f87"
down_revision = "f84e336e4ffb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), server_onupdate=sa.func.now()),
    )
    op.create_index(op.f("ix_permissions_name"), "permissions", ["name"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), server_onupdate=sa.func.now()),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    _seed_default_permissions()
    _seed_default_roles()
    _link_default_role_permissions()


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_permissions_name"), table_name="permissions")
    op.drop_table("permissions")


def _seed_default_permissions() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=128)),
        sa.column("description", sa.String(length=255)),
    )

    op.bulk_insert(
        permissions_table,
        [
            {"name": "users:read", "description": "Read user records"},
            {"name": "users:manage", "description": "Create, update, and delete user records"},
        ],
    )


def _seed_default_roles() -> None:
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=64)),
        sa.column("description", sa.String(length=255)),
    )

    op.bulk_insert(
        roles_table,
        [
            {"name": "admin", "description": "Administrators with full access"},
            {"name": "member", "description": "Standard member role"},
        ],
    )


def _link_default_role_permissions() -> None:
    bind = op.get_bind()

    permission_lookup = _fetch_lookup(
        bind.execute(
            sa.text(
                "SELECT id, name FROM permissions WHERE name IN (:read, :manage)"
            ),
            {"read": "users:read", "manage": "users:manage"},
        ).fetchall()
    )
    role_lookup = _fetch_lookup(
        bind.execute(
            sa.text("SELECT id, name FROM roles WHERE name IN (:admin, :member)"),
            {"admin": "admin", "member": "member"},
        ).fetchall()
    )

    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer()),
        sa.column("permission_id", sa.Integer()),
    )

    op.bulk_insert(
        role_permissions_table,
        [
            {
                "role_id": role_lookup["admin"],
                "permission_id": permission_lookup["users:manage"],
            },
            {
                "role_id": role_lookup["admin"],
                "permission_id": permission_lookup["users:read"],
            },
        ],
    )


def _fetch_lookup(rows: Sequence[Mapping[str, int] | tuple[int, str]]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for row in rows:
        if isinstance(row, Mapping):
            identifier = int(row["id"])
            name = str(row["name"])
        else:
            identifier, name = row
        lookup[name] = identifier
    return lookup

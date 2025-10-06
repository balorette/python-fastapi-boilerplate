"""CLI commands for application management."""

import asyncio
import getpass

import typer

from app.core.database import (
    close_database_connections,
    get_async_db_context,
    init_database,
)
from app.core.exceptions import ConflictError
from app.schemas.user import UserCreate
from app.services.user import UserService

app = typer.Typer()


async def create_admin_user(
    username: str, email: str, password: str, full_name: str | None = None
) -> None:
    """Create an admin user using enhanced database context."""
    async with get_async_db_context() as session:
        user_service = UserService(session)

        try:
            # Create admin user data
            admin_data = UserCreate(
                username=username,
                email=email,
                password=password,
                confirm_password=password,
                full_name=full_name or f"Admin {username}",
                is_superuser=True,
                is_active=True,
            )

            # Create the admin user
            admin_user = await user_service.create_user(admin_data)
            # Note: commit is handled by the context manager

            typer.echo(f"✅ Admin user '{username}' created successfully!")
            typer.echo(f"   Email: {admin_user.email}")
            typer.echo(f"   ID: {admin_user.id}")

        except ConflictError as exc:
            typer.echo(f"❌ Error: {exc}")
            raise typer.Exit(1) from exc
        except Exception as exc:
            typer.echo(f"❌ Unexpected error: {exc}")
            raise typer.Exit(1) from exc


@app.command()
def init_admin(
    username: str = typer.Option(..., "--username", "-u", help="Admin username"),
    email: str = typer.Option(..., "--email", "-e", help="Admin email"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Admin password (will prompt if not provided)"
    ),
    full_name: str | None = typer.Option(
        None, "--full-name", "-n", help="Admin full name"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Create an initial admin user."""

    # Get password if not provided
    if not password:
        password = getpass.getpass("Enter admin password: ")
        confirm_password = getpass.getpass("Confirm admin password: ")

        if password != confirm_password:
            typer.echo("❌ Passwords do not match!")
            raise typer.Exit(1)

    # Confirm creation unless force flag is used
    if not force:
        typer.echo("\nCreating admin user:")
        typer.echo(f"  Username: {username}")
        typer.echo(f"  Email: {email}")
        typer.echo(f"  Full Name: {full_name or f'Admin {username}'}")

        if not typer.confirm("\nProceed with admin user creation?"):
            typer.echo("Admin user creation cancelled.")
            raise typer.Exit(0)

    # Create the admin user
    async def _create_user_and_cleanup():
        try:
            await create_admin_user(username, email, password, full_name)
        finally:
            # Ensure proper database cleanup
            await close_database_connections()

    try:
        asyncio.run(_create_user_and_cleanup())
    except KeyboardInterrupt:
        typer.echo("\n❌ Admin user creation cancelled.")
        raise typer.Exit(1) from None


@app.command()
def init_db():
    """Initialize the database by creating all tables."""

    async def _init_db():
        try:
            await init_database()
            typer.echo("✅ Database initialized successfully!")
        except Exception as exc:
            typer.echo(f"❌ Error initializing database: {exc}")
            raise

    try:
        asyncio.run(_init_db())
    except Exception as exc:
        typer.echo(f"❌ Database initialization failed: {exc}")
        raise typer.Exit(1) from exc


@app.command()
def setup(
    username: str = typer.Option("admin", "--username", "-u", help="Admin username"),
    email: str = typer.Option("admin@example.com", "--email", "-e", help="Admin email"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Admin password (will prompt if not provided)"
    ),
    full_name: str | None = typer.Option(
        "System Administrator", "--full-name", "-n", help="Admin full name"
    ),
) -> None:
    """Complete setup: initialize database and create admin user."""

    typer.echo("🚀 Setting up the application...")

    # Get password if not provided
    if not password:
        password = getpass.getpass("Enter admin password: ")
        confirm_password = getpass.getpass("Confirm admin password: ")

        if password != confirm_password:
            typer.echo("❌ Passwords do not match!")
            raise typer.Exit(1)

    async def _complete_setup():
        try:
            # Initialize database
            typer.echo("\n1. Initializing database...")
            await init_database()
            typer.echo("✅ Database initialized successfully!")

            # Create admin user
            typer.echo("\n2. Creating admin user...")
            await create_admin_user(username, email, password, full_name)
            typer.echo("✅ Admin user created successfully!")

        except Exception as exc:
            typer.echo(f"❌ Setup failed: {exc}")
            raise
        finally:
            # Ensure proper database cleanup
            await close_database_connections()

    try:
        asyncio.run(_complete_setup())
    except Exception as exc:
        typer.echo(f"❌ Setup failed: {exc}")
        raise typer.Exit(1) from exc

    typer.echo("\n🎉 Application setup completed successfully!")
    typer.echo("\n📝 Admin credentials:")
    typer.echo(f"   Username: {username}")
    typer.echo(f"   Email: {email}")
    typer.echo("\n🔗 You can now start the server and login at: /api/v1/auth/login")


if __name__ == "__main__":
    app()

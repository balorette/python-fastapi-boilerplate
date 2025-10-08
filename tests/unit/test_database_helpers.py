"""Unit tests for the database helpers in app.core.database."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.exc import DisconnectionError

from app.core import database


class DummyResult:
    """Simple result wrapper mirroring SQLAlchemy scalar behaviour."""

    def __init__(self, value: Any):
        self._value = value

    def scalar(self) -> Any:
        return self._value


class DummySession:
    """Lightweight async session double used across tests."""

    def __init__(self, *, should_fail: bool = False, result_value: Any = None):
        self.should_fail = should_fail
        self.result_value = result_value
        self.commit_called = False
        self.rollback_called = False
        self.close_called = False

    async def execute(self, _query: Any) -> DummyResult:
        if self.should_fail:
            raise DisconnectionError("temporary connection drop")
        return DummyResult(self.result_value)

    async def commit(self) -> None:
        self.commit_called = True

    async def rollback(self) -> None:
        self.rollback_called = True

    async def close(self) -> None:
        self.close_called = True


@pytest.mark.asyncio
async def test_get_async_db_retries_then_yields_session(monkeypatch):
    """`get_async_db` should retry on disconnection and eventually yield a session."""

    attempts: list[DummySession] = []

    def fake_session_factory() -> DummySession:
        session = DummySession(should_fail=len(attempts) == 0, result_value=1)
        attempts.append(session)
        return session

    sleep_calls: list[float] = []

    async def fake_sleep(
        delay: float,
    ) -> None:  # pragma: no cover - exercised indirectly
        sleep_calls.append(delay)

    monkeypatch.setattr(database, "AsyncSessionLocal", fake_session_factory)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    generator = database.get_async_db()

    session = await generator.__anext__()
    assert isinstance(session, DummySession)

    with pytest.raises(StopAsyncIteration):
        await generator.asend(None)

    assert len(attempts) == 2
    assert attempts[0].rollback_called is True
    assert attempts[0].close_called is True
    assert attempts[1].commit_called is True
    assert attempts[1].close_called is True
    # Exponential backoff should have been triggered once for the retry
    assert sleep_calls == [2.0]


@pytest.mark.asyncio
async def test_get_async_db_raises_after_max_retries(monkeypatch):
    """`get_async_db` should surface connection errors after exhausting retries."""

    attempts: list[DummySession] = []

    def failing_session_factory() -> DummySession:
        session = DummySession(should_fail=True)
        attempts.append(session)
        return session

    async def fake_sleep(_delay: float) -> None:
        pass

    monkeypatch.setattr(database, "AsyncSessionLocal", failing_session_factory)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    generator = database.get_async_db()
    with pytest.raises(DisconnectionError):
        await generator.__anext__()

    # All sessions should have been closed after each failed attempt
    assert len(attempts) == 3
    assert all(session.close_called for session in attempts)
    assert all(session.rollback_called for session in attempts)


def test_get_engine_config_sqlite(monkeypatch, tmp_path):
    """SQLite engines should include StaticPool and WAL pragmas."""

    sqlite_db = tmp_path / "db.sqlite3"
    settings_stub = SimpleNamespace(
        DEBUG=False,
        DATABASE_URL=f"sqlite:///{sqlite_db}",
        DATABASE_URL_ASYNC=f"sqlite+aiosqlite:///{sqlite_db}",
        DATABASE_TYPE="sqlite",
        is_sqlite=True,
        is_postgresql=False,
    )
    monkeypatch.setattr(database, "settings", settings_stub)

    engine_kwargs, async_engine_kwargs = database.get_engine_config()

    assert engine_kwargs["poolclass"].__name__ == "StaticPool"
    assert engine_kwargs["connect_args"]["check_same_thread"] is False
    assert "timeout" in engine_kwargs["connect_args"]
    assert async_engine_kwargs["pool_pre_ping"] is True


def test_get_engine_config_postgresql(monkeypatch):
    """PostgreSQL engines should request queue pool parameters and async connect args."""

    settings_stub = SimpleNamespace(
        DEBUG=True,
        DATABASE_URL="postgresql://example/db",
        DATABASE_URL_ASYNC="postgresql+asyncpg://example/db",
        DATABASE_TYPE="postgresql",
        is_sqlite=False,
        is_postgresql=True,
    )
    monkeypatch.setattr(database, "settings", settings_stub)

    engine_kwargs, async_engine_kwargs = database.get_engine_config()

    assert engine_kwargs["poolclass"].__name__ == "QueuePool"
    assert engine_kwargs["pool_pre_ping"] is True
    assert (
        async_engine_kwargs["connect_args"]["server_settings"]["application_name"]
        == "fastapi_app"
    )


@pytest.mark.asyncio
async def test_check_database_health_handles_errors(monkeypatch):
    """`check_database_health` should capture exceptions as error metadata."""

    @asynccontextmanager
    async def failing_context():
        raise RuntimeError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(database, "get_async_db_context", failing_context)
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(DATABASE_TYPE="sqlite", is_postgresql=False),
    )

    health = await database.check_database_health()
    assert health["connection_status"] == "error"
    assert health["error"] == "boom"


@pytest.mark.asyncio
async def test_validate_connection_success(monkeypatch):
    """`validate_connection` should return True when the test query succeeds."""

    session = DummySession(result_value=1)

    @asynccontextmanager
    async def successful_context():
        yield session

    monkeypatch.setattr(database, "get_async_db_context", successful_context)

    assert await database.validate_connection() is True
    assert session.commit_called is False
    assert session.close_called is False


@pytest.mark.asyncio
async def test_get_async_db_context_manages_session(monkeypatch):
    """`get_async_db_context` should commit and close sessions on success."""

    session = DummySession(result_value=1)

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    async with database.get_async_db_context() as yielded_session:
        assert yielded_session is session

    assert session.commit_called is True
    assert session.close_called is True


@pytest.mark.asyncio
async def test_close_database_connections_disposes_engines(monkeypatch):
    """`close_database_connections` should dispose both async and sync engines."""

    class DummyAsyncEngine:
        def __init__(self) -> None:
            self.disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    class DummyEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    async_engine = DummyAsyncEngine()
    engine = DummyEngine()

    monkeypatch.setattr(database, "async_engine", async_engine)
    monkeypatch.setattr(database, "engine", engine)

    await database.close_database_connections()

    assert async_engine.disposed is True
    assert engine.disposed is True


@pytest.mark.asyncio
async def test_create_tables_sqlite(monkeypatch):
    """`create_tables` should call metadata.create_all when using SQLite."""

    create_calls: list[Any] = []

    def fake_create_all(*_args, **_kwargs) -> None:
        create_calls.append(True)

    monkeypatch.setattr(database.Base.metadata, "create_all", fake_create_all)
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(
            is_sqlite=True,
            is_postgresql=False,
            DATABASE_TYPE="sqlite",
            DATABASE_URL="sqlite:///./test.db",
        ),
    )

    await database.create_tables()

    assert create_calls


@pytest.mark.asyncio
async def test_create_tables_postgresql(monkeypatch):
    """PostgreSQL table creation should run metadata via async engine."""

    create_calls: list[Any] = []

    def fake_create_all(_bind=None) -> None:
        create_calls.append(True)

    monkeypatch.setattr(database.Base.metadata, "create_all", fake_create_all)

    class DummyConnection:
        def __init__(self) -> None:
            self.sync_called = False

        async def __aenter__(self) -> DummyConnection:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def run_sync(self, func):
            self.sync_called = True
            func("connection")

    class DummyAsyncEngine:
        def __init__(self) -> None:
            self.connection = DummyConnection()

        @asynccontextmanager
        async def begin(self):
            yield self.connection

    dummy_engine = DummyAsyncEngine()

    monkeypatch.setattr(database, "async_engine", dummy_engine)
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(
            is_sqlite=False,
            is_postgresql=True,
            DATABASE_TYPE="postgresql",
        ),
    )

    await database.create_tables()

    assert dummy_engine.connection.sync_called is True
    assert create_calls


@pytest.mark.asyncio
async def test_init_database_success(monkeypatch):
    """`init_database` should create tables and seed default roles."""

    health_calls: list[Any] = []
    create_called: list[Any] = []
    ensure_called: list[Any] = []

    async def fake_check_health() -> dict[str, Any]:
        health_calls.append(True)
        return {"connection_status": "healthy"}

    async def fake_create_tables() -> None:
        create_called.append(True)

    async def fake_ensure_default_roles(_session) -> None:
        ensure_called.append(True)

    class DummySession:
        async def __aenter__(self) -> DummySession:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(database, "check_database_health", fake_check_health)
    monkeypatch.setattr(database, "create_tables", fake_create_tables)
    monkeypatch.setattr(database, "ensure_default_roles", fake_ensure_default_roles)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(
            DATABASE_TYPE="sqlite",
            is_sqlite=True,
            DATABASE_URL="sqlite:///./test.db",
        ),
    )

    await database.init_database()

    assert health_calls
    assert create_called
    assert ensure_called


@pytest.mark.asyncio
async def test_init_database_health_failure(monkeypatch):
    """`init_database` should raise when the health check fails."""

    async def fake_check_health() -> dict[str, Any]:
        return {"connection_status": "error"}

    monkeypatch.setattr(database, "check_database_health", fake_check_health)
    monkeypatch.setattr(
        database, "settings", SimpleNamespace(DATABASE_TYPE="sqlite", is_sqlite=True)
    )

    with pytest.raises(RuntimeError):
        await database.init_database()


@pytest.mark.asyncio
async def test_check_database_health_success(monkeypatch):
    """Healthy connections should include pool status metadata."""

    session = DummySession(result_value=1)

    @asynccontextmanager
    async def successful_context():
        yield session

    monkeypatch.setattr(database, "get_async_db_context", successful_context)
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(DATABASE_TYPE="postgresql", is_postgresql=True),
    )
    monkeypatch.setattr(database, "async_engine", SimpleNamespace(pool=object()))

    health = await database.check_database_health()

    assert health["connection_status"] == "healthy"
    assert health["pool_status"]["pool_available"] is True

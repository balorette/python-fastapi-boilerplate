"""CLI smoke tests using Typer's CliRunner."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from typer.testing import CliRunner

from app import cli

pytestmark = pytest.mark.smoke


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _run_async(func, *args, **kwargs):
    return asyncio.get_event_loop().run_until_complete(func(*args, **kwargs))


def test_init_db_invokes_initializer(monkeypatch, runner: CliRunner):
    calls: dict[str, bool] = {"init": False}

    async def fake_init_database() -> None:
        calls["init"] = True

    monkeypatch.setattr(cli, "init_database", fake_init_database)

    result = runner.invoke(cli.app, ["init-db"])

    assert result.exit_code == 0
    assert calls["init"] is True


def test_init_admin_uses_create_admin_user(monkeypatch, runner: CliRunner):
    calls: dict[str, int] = {"create": 0, "close": 0}

    async def fake_create_admin_user(*_args: Any, **_kwargs: Any) -> None:
        calls["create"] += 1

    async def fake_close_connections() -> None:
        calls["close"] += 1

    monkeypatch.setattr(cli, "create_admin_user", fake_create_admin_user)
    monkeypatch.setattr(cli, "close_database_connections", fake_close_connections)

    result = runner.invoke(
        cli.app,
        [
            "init-admin",
            "--username",
            "tester",
            "--email",
            "tester@example.com",
            "--password",
            "Password123!",
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert calls["create"] == 1
    assert calls["close"] == 1


def test_setup_initializes_and_creates_admin(monkeypatch, runner: CliRunner):
    sequence: list[str] = []

    async def fake_init_database() -> None:
        sequence.append("init")

    async def fake_create_admin_user(*_args: Any, **_kwargs: Any) -> None:
        sequence.append("create")

    async def fake_close_database_connections() -> None:
        sequence.append("close")

    monkeypatch.setattr(cli, "init_database", fake_init_database)
    monkeypatch.setattr(cli, "create_admin_user", fake_create_admin_user)
    monkeypatch.setattr(
        cli, "close_database_connections", fake_close_database_connections
    )

    result = runner.invoke(
        cli.app,
        [
            "setup",
            "--username",
            "admin",
            "--email",
            "admin@example.com",
            "--password",
            "Password123!",
        ],
    )

    assert result.exit_code == 0
    assert sequence == ["init", "create", "close"]

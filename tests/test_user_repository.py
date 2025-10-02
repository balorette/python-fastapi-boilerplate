"""Tests for the user repository advanced helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.repositories.user import UserRepository
from app.schemas.user import UserCreate
from app.services.user import UserService


@pytest.mark.asyncio
async def test_user_repository_filters(async_db_session):
    """User repository should support active filters and date ranges."""
    repo = UserRepository(async_db_session)

    # Seed active and inactive users
    service = UserService(async_db_session)

    user_active = UserCreate(
        username="active_user",
        email="active@example.com",
        password="Secret123!",
        confirm_password="Secret123!",
        full_name="Active User",
        is_active=True,
        is_superuser=False,
    )
    user_inactive = UserCreate(
        username="inactive_user",
        email="inactive@example.com",
        password="Secret123!",
        confirm_password="Secret123!",
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )

    active_created = await service.create_user(user_active)
    inactive_created = await service.create_user(user_inactive)

    # Force creation timestamps for deterministic date filters
    active_created.created_at = datetime.now(UTC)
    inactive_created.created_at = datetime.now(UTC) - timedelta(days=45)
    await async_db_session.commit()

    # Active filter is handled via count/get_multi
    filters = {"is_active": True}
    active_total = await repo.count_records(filters)
    assert active_total == 1

    active_users = await repo.get_multi(filters=filters)
    assert len(active_users) == 1
    assert active_users[0].email == "active@example.com"

    # Date range filter should only include recent records
    date_range_users = await repo.get_users_by_creation_date(
        start_date=(datetime.now(UTC) - timedelta(days=30)).isoformat(),
        end_date=datetime.now(UTC).isoformat(),
    )
    assert any(user.email == "active@example.com" for user in date_range_users)
    assert all(user.email != "inactive@example.com" for user in date_range_users)


@pytest.mark.asyncio
async def test_user_repository_search(async_db_session):
    """Search helpers should support fuzzy matching and pagination."""
    repo = UserRepository(async_db_session)

    alpha = await repo.create(
        {
            "username": "alpha",
            "email": "alpha@example.com",
            "hashed_password": "hash",
            "full_name": "Alpha User",
        }
    )
    await repo.create(
        {
            "username": "beta",
            "email": "beta@example.com",
            "hashed_password": "hash",
            "full_name": "Beta User",
        }
    )

    results = await repo.search_users("alp")
    assert len(results) == 1
    assert results[0].id == alpha.id

    paged = await repo.search_users("a", skip=0, limit=1)
    assert len(paged) == 1

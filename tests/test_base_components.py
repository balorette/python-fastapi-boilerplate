"""Tests for the shared base repository and service helpers."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import Boolean, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.services.base import (
    BaseService,
    BusinessRuleViolationError,
    DuplicateEntityError,
)


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)


class WidgetRepository(BaseRepository[Widget]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Widget, session)


class WidgetService(BaseService):
    def __init__(self) -> None:
        super().__init__("widget")


@pytest_asyncio.fixture(scope="module")
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_crud_and_pagination(async_session: AsyncSession):
    repo = WidgetRepository(async_session)

    widget = await repo.create(
        {"id": str(uuid.uuid4()), "name": "Alpha"}, user_id="tester"
    )

    fetched = await repo.get_by_id(widget.id)
    assert fetched is not None
    assert fetched.name == "Alpha"
    assert fetched.created_by == "tester"

    assert await repo.exists(field_name="name", field_value="Alpha")

    pagination = PaginationParams(skip=0, limit=1)
    paginated = await repo.paginate(pagination=pagination)
    assert paginated.total == 1
    assert paginated.total_pages == 1
    assert paginated.items[0].name == "Alpha"

    updated = await repo.update(widget, {"name": "Beta"})
    assert updated is not None
    assert updated.name == "Beta"

    deleted = await repo.delete(widget.id, soft_delete=True)
    assert deleted is True

    soft_deleted = await repo.get_by_id(widget.id)
    assert soft_deleted is not None
    assert soft_deleted.is_active is False

    hard_deleted = await repo.delete(widget.id, soft_delete=False)
    assert hard_deleted is True
    assert await repo.get_by_id(widget.id) is None


@pytest.mark.asyncio
async def test_service_helpers_validate_business_logic(async_session: AsyncSession):
    repo = WidgetRepository(async_session)
    service = WidgetService()

    widget_id = str(uuid.uuid4())
    await repo.create({"id": widget_id, "name": "Gamma"})

    with pytest.raises(BusinessRuleViolationError):
        service._validate_business_rules({"must_pass": False})

    await service._validate_entity_exists(
        async_session, repo, widget_id, entity_name="Widget"
    )

    with pytest.raises(DuplicateEntityError):
        await service._validate_unique_field(
            async_session,
            repo,
            field_name="name",
            field_value="Gamma",
            entity_name="Widget",
        )

    sanitized = service._sanitize_update_data(
        {"name": "Gamma", "ignored": None, "secret": "value"},
        allowed_fields={"name", "secret"},
        forbidden_fields={"secret"},
    )
    assert sanitized == {"name": "Gamma"}

    pagination = PaginationParams(skip=0, limit=10)
    response = await service.paginate(async_session, repo, pagination=pagination)
    assert response.total >= 1

"""Unified base repository implementation with integrity helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypeVar

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.schemas.pagination import PaginatedResponse, PaginationParams

ModelType = TypeVar("ModelType")


class RepositoryError(Exception):
    """Base exception raised by repository operations."""


class DataIntegrityError(RepositoryError):
    """Raised when database constraints are violated."""


class BaseRepository[ModelType]:
    """Reusable repository providing CRUD, filtering, and pagination helpers."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
        self.logger = logging.getLogger(f"app.repositories.{model.__name__}")
        self._write_lock = asyncio.Lock()

    def _resolve_session(self, session: AsyncSession | None) -> AsyncSession:
        if session is not None:
            return session
        if self.session is None:
            raise RepositoryError(
                "AsyncSession is not available for repository operation"
            )
        return self.session

    async def get(
        self,
        id: Any,
        *,
        load_relationships: Any = None,
        session: AsyncSession | None = None,
    ) -> ModelType | None:
        """Get a single record by ID with optional relationship loading."""

        session = self._resolve_session(session)
        stmt = select(self.model).where(self.model.id == id)

        if load_relationships:
            if load_relationships is True:
                relationship_keys = [
                    rel.key for rel in self.model.__mapper__.relationships
                ]
            elif isinstance(load_relationships, (list, tuple, set)):
                relationship_keys = list(load_relationships)
            else:
                relationship_keys = []

            for relation in relationship_keys:
                attribute = getattr(self.model, relation, None)
                if attribute is not None:
                    stmt = stmt.options(selectinload(attribute))

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        id: Any,
        *,
        load_relationships: bool = False,
        session: AsyncSession | None = None,
    ) -> ModelType | None:
        """Alias for :meth:`get` to match newer repository interface."""

        return await self.get(
            id, load_relationships=load_relationships, session=session
        )

    async def get_by_field(
        self,
        field_name: str,
        field_value: Any,
        *,
        session: AsyncSession | None = None,
    ) -> ModelType | None:
        """Return the first record matching ``field_name == field_value``."""

        session = self._resolve_session(session)
        field = getattr(self.model, field_name)
        stmt = select(self.model).where(field == field_value)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        session: AsyncSession | None = None,
        load_relationships: list[str] | None = None,
    ) -> list[ModelType]:
        """Return multiple records with optional filtering and ordering."""

        session = self._resolve_session(session)
        stmt = select(self.model)

        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    attr = getattr(self.model, key)
                    if isinstance(value, list):
                        conditions.append(attr.in_(value))
                    elif isinstance(value, dict):
                        if "gte" in value:
                            conditions.append(attr >= value["gte"])
                        if "lte" in value:
                            conditions.append(attr <= value["lte"])
                        if "gt" in value:
                            conditions.append(attr > value["gt"])
                        if "lt" in value:
                            conditions.append(attr < value["lt"])
                    else:
                        conditions.append(attr == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                if hasattr(self.model, field_name):
                    stmt = stmt.order_by(getattr(self.model, field_name).desc())
            else:
                if hasattr(self.model, order_by):
                    stmt = stmt.order_by(getattr(self.model, order_by))
        else:
            stmt = stmt.order_by(self.model.id)

        if load_relationships:
            for relation in load_relationships:
                attribute = getattr(self.model, relation, None)
                if attribute is not None:
                    stmt = stmt.options(selectinload(attribute))

        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        *,
        pagination: PaginationParams | None = None,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        session: AsyncSession | None = None,
        load_relationships: list[str] | None = None,
    ) -> list[ModelType]:
        """Helper mirroring the newer repository interface."""

        pagination = pagination or PaginationParams(
            skip=0, limit=100, order_by=order_by
        )
        return await self.get_multi(
            skip=pagination.skip,
            limit=pagination.limit,
            filters=filters,
            order_by=order_by or pagination.order_by,
            session=session,
            load_relationships=load_relationships,
        )

    async def paginate(
        self,
        *,
        pagination: PaginationParams,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        session: AsyncSession | None = None,
        load_relationships: list[str] | None = None,
    ) -> PaginatedResponse[ModelType]:
        """Return a paginated response matching the newer interface."""

        items = await self.list(
            pagination=pagination,
            filters=filters,
            order_by=order_by,
            session=session,
            load_relationships=load_relationships,
        )
        total = await self.count_records(filters=filters, session=session)
        return PaginatedResponse.create(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )

    async def create(
        self,
        obj_in: dict[str, Any],
        *,
        session: AsyncSession | None = None,
        user_id: str | None = None,
    ) -> ModelType:
        """Create a new record with commit and refresh semantics."""

        session = self._resolve_session(session)
        async with self._write_lock:
            db_obj = self.model(**obj_in)

            if hasattr(db_obj, "created_by") and user_id:
                db_obj.created_by = user_id
            if hasattr(db_obj, "updated_by") and user_id:
                db_obj.updated_by = user_id

            try:
                session.add(db_obj)
                await session.commit()
                await session.refresh(db_obj)
                self.logger.debug("Created %s", self.model.__name__)
                return db_obj
            except IntegrityError as exc:
                await session.rollback()
                self.logger.error("Integrity error during create", exc_info=True)
                raise DataIntegrityError(str(exc)) from exc
            except Exception as exc:
                await session.rollback()
                self.logger.error("Unexpected error during create", exc_info=True)
                raise RepositoryError(str(exc)) from exc

    async def update(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any],
        *,
        session: AsyncSession | None = None,
    ) -> ModelType:
        """Update an existing record with commit/refresh semantics."""

        session = self._resolve_session(session)
        async with self._write_lock:
            for field, value in obj_in.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)

            try:
                await session.commit()
                await session.refresh(db_obj)
                self.logger.debug("Updated %s", self.model.__name__)
                return db_obj
            except IntegrityError as exc:
                await session.rollback()
                self.logger.error("Integrity error during update", exc_info=True)
                raise DataIntegrityError(str(exc)) from exc
            except Exception as exc:
                await session.rollback()
                self.logger.error("Unexpected error during update", exc_info=True)
                raise RepositoryError(str(exc)) from exc

    async def delete(
        self,
        id: Any,
        *,
        session: AsyncSession | None = None,
        soft_delete: bool = False,
    ) -> bool:
        """Delete a record by ID, optionally performing a soft delete."""

        session = self._resolve_session(session)
        db_obj = await self.get(id, session=session)
        if not db_obj:
            return False

        async with self._write_lock:
            try:
                if soft_delete and hasattr(db_obj, "is_active"):
                    db_obj.is_active = False
                    await session.commit()
                    await session.refresh(db_obj)
                    self.logger.debug("Soft deleted %s", self.model.__name__)
                    return True

                await session.delete(db_obj)
                await session.commit()
                self.logger.debug("Deleted %s", self.model.__name__)
                return True
            except Exception as exc:
                await session.rollback()
                self.logger.error("Error during delete", exc_info=True)
                raise RepositoryError(str(exc)) from exc

    async def count_records(
        self,
        filters: dict[str, Any] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> int:
        """Count records with optional filtering."""

        session = self._resolve_session(session)
        stmt = select(func.count()).select_from(self.model)

        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    attr = getattr(self.model, key)
                    if isinstance(value, list):
                        conditions.append(attr.in_(value))
                    elif isinstance(value, dict):
                        if "gte" in value:
                            conditions.append(attr >= value["gte"])
                        if "lte" in value:
                            conditions.append(attr <= value["lte"])
                        if "gt" in value:
                            conditions.append(attr > value["gt"])
                        if "lt" in value:
                            conditions.append(attr < value["lt"])
                    else:
                        conditions.append(attr == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count(
        self,
        *,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> int:
        """Alias for :meth:`count_records` matching newer interface."""

        return await self.count_records(filters, session=session)

    async def record_exists(
        self,
        id: Any,
        *,
        session: AsyncSession | None = None,
    ) -> bool:
        """Check if record exists by ID."""

        session = self._resolve_session(session)
        stmt = select(self.model.id).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists(
        self,
        *,
        field_name: str,
        field_value: Any,
        exclude_id: Any | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """Check if a record exists for the given field/value pair."""

        session = self._resolve_session(session)
        field = getattr(self.model, field_name)
        stmt = select(self.model.id).where(field == field_value)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

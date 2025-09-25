"""Enhanced base repository pattern implementation."""

from typing import Any, Generic, TypeVar

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Enhanced base repository with comprehensive CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Any, load_relationships: bool = False) -> ModelType | None:
        """Get a single record by ID with optional relationship loading."""
        stmt = select(self.model).where(self.model.id == id)

        if load_relationships:
            # Auto-load all relationships
            stmt = stmt.options(selectinload("*"))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None
    ) -> list[ModelType]:
        """Enhanced get_multi with ordering and advanced filtering support."""
        stmt = select(self.model)

        # Apply filters
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    attr = getattr(self.model, key)
                    if isinstance(value, list):
                        conditions.append(attr.in_(value))
                    elif isinstance(value, dict):
                        # Support for range queries like {"gte": 10, "lte": 20}
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

        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                # Descending order
                order_field = order_by[1:]
                if hasattr(self.model, order_field):
                    stmt = stmt.order_by(getattr(self.model, order_field).desc())
            else:
                # Ascending order
                if hasattr(self.model, order_by):
                    stmt = stmt.order_by(getattr(self.model, order_by))
        else:
            # Default order by id
            stmt = stmt.order_by(self.model.id)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Create with better error handling."""
        try:
            db_obj = self.model(**obj_in)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            raise e

    async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """Update with better validation and error handling."""
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)

            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            raise e

    async def delete(self, id: Any) -> bool:
        """Delete with better error handling."""
        try:
            db_obj = await self.get(id)
            if db_obj:
                await self.session.delete(db_obj)
                await self.session.commit()
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            raise e

    async def count_records(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filtering."""
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

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def record_exists(self, id: Any) -> bool:
        """Check if record exists."""
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filtering."""
        stmt = select(self.model)

        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return len(list(result.scalars().all()))

    async def exists(self, id: Any) -> bool:
        """Check if a record exists by ID."""
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

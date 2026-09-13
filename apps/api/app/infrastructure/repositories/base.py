from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import Base
from app.infrastructure.models.common import TenantRow

ModelType = TypeVar("ModelType", bound=TenantRow)


# M2 FINAL SYNCHRONIZATION
class BaseRepository(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: type[ModelType], institution_id: UUID):
        self.session = session
        self.model = model
        self.institution_id = institution_id

    async def get_by_id(self, id: UUID) -> ModelType | None:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.institution_id == self.institution_id)
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.institution_id == self.institution_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def exists(self, id: UUID) -> bool:
        result = await self.session.execute(
            select(
                exists().where(
                    self.model.institution_id == self.institution_id, self.model.id == id
                )
            )
        )
        return result.scalar() or False


class MutableRepository(BaseRepository[ModelType]):
    async def create(self, **kwargs: Any) -> ModelType:
        kwargs["institution_id"] = self.institution_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        if instance.institution_id != self.institution_id:
            raise ValueError(
                "Tenant isolation violation: cannot update instance from another institution"
            )

        # Don't allow updating institution_id
        kwargs.pop("institution_id", None)

        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        if instance.institution_id != self.institution_id:
            raise ValueError(
                "Tenant isolation violation: cannot delete instance from another institution"
            )
        await self.session.delete(instance)
        await self.session.flush()


class EventRepository(BaseRepository[ModelType]):
    async def append(self, **kwargs: Any) -> ModelType:
        kwargs["institution_id"] = self.institution_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance


class DefinitionRepository(BaseRepository[ModelType]):
    async def create_version(self, **kwargs: Any) -> ModelType:
        kwargs["institution_id"] = self.institution_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def transition_lifecycle(self, instance: ModelType, new_status: str) -> ModelType:
        if instance.institution_id != self.institution_id:
            raise ValueError("Tenant isolation violation")
        instance.status = new_status
        await self.session.flush()
        return instance

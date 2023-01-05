from collections.abc import Sequence
from functools import lru_cache
from typing import Type, Any, Optional, TypeVar

from tortoise.queryset import QuerySet
from tortoise.transactions import in_transaction

from . import Model
from ex_fastapi.routers.base_crud_service import BaseCRUDService, PK, SCHEMA
from ex_fastapi.routers.crud_router import ItemNotFound, NotUnique


TORTOISE_MODEL = TypeVar('TORTOISE_MODEL', bound=Model)


class TortoiseCRUDService(BaseCRUDService[PK, TORTOISE_MODEL]):
    model: Type[TORTOISE_MODEL]
    queryset_select_related: Sequence[str]
    queryset_prefetch_related: Sequence[str]
    queryset_default_filters: dict[str, Any]

    def __init__(
            self,
            db_model: Type[TORTOISE_MODEL],
            *,
            read_schema: Type[SCHEMA] = None,
            read_list_item_schema: Type[SCHEMA] = None,
            create_schema: Type[SCHEMA] = None,
            edit_schema: Type[SCHEMA] = None,
            queryset_select_related: Sequence[str] = None,
            queryset_prefetch_related: Sequence[str] = None,
            queryset_default_filters: dict[str, Any] = None,
            **kwargs,
    ):
        self.model = db_model
        self.pk_field_type = self.model._meta.pk.field_type
        self._pk = self.model._meta.pk_attr

        self.read_schema = read_schema
        self.list_item_schema = read_list_item_schema or self.read_schema
        self.create_schema = create_schema
        self.edit_schema = edit_schema

        self.queryset_select_related = queryset_select_related
        self.queryset_prefetch_related = queryset_prefetch_related
        self.queryset_default_filters = queryset_default_filters
        super().__init__(**kwargs)

    @lru_cache
    def get_queryset(self) -> QuerySet[TORTOISE_MODEL]:
        query = self.model.all()
        if self.queryset_default_filters:
            query = query.filter(**self.queryset_default_filters)
        if self.queryset_select_related:
            query = query.select_related(*self.queryset_select_related)
        if self.queryset_prefetch_related:
            query = query.prefetch_related(*self.queryset_prefetch_related)
        return query

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: list[str],
            # filters:
            **kwargs
    ) -> tuple[list[TORTOISE_MODEL], int]:
        query = self.get_queryset()
        total_query = query.count()
        if sort:
            query = query.order_by(*sort)
        if skip:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)
        async with in_transaction():
            result = await query
            count = await total_query
        return result, count

    def _get_many_queryset(self, item_ids: list[PK]) -> QuerySet[TORTOISE_MODEL]:
        return self.get_queryset().filter(**{f'{self._pk}__in': item_ids})

    async def get_many(self, item_ids: list[PK], *args, **kwargs) -> list[TORTOISE_MODEL]:
        return await self._get_many_queryset(item_ids)

    async def get_one(self, item_id: PK, *args, **kwargs) -> Optional[TORTOISE_MODEL]:
        item = await self.get_queryset().get_or_none(**{self._pk: item_id})
        if item is None:
            raise ItemNotFound
        return item

    async def create(self, data: SCHEMA, exclude: set[str] = None, *args, **kwargs) -> TORTOISE_MODEL:
        if not_unique_fields := await self.model.check_unique(data.dict()):
            raise NotUnique(fields=not_unique_fields)
        instance: TORTOISE_MODEL = self.model(**data.dict(exclude=exclude), **kwargs)
        await instance.save(force_create=True)
        return instance

    async def edit(self, item_id: PK, data: SCHEMA, *args, **kwargs) -> TORTOISE_MODEL:
        if not_unique_fields := await self.model.check_unique(data.dict(exclude_none=True, exclude_unset=True)):
            raise NotUnique(fields=not_unique_fields)
        item = await self.get_one(item_id, *args, **kwargs)
        await item.update_from_dict(data.dict(exclude_unset=True))
        await item.save(force_update=True)
        return item

    async def delete_many(self, item_ids: list[PK], *args, **kwargs) -> int:
        return await self._get_many_queryset(item_ids).delete()

    async def delete_one(self, item_id: PK, *args, **kwargs) -> None:
        item = await self.get_one(item_id, *args, **kwargs)
        await item.delete()

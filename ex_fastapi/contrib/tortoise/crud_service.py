from collections import defaultdict
from collections.abc import Sequence
from typing import Type, Any, Optional, TypeVar

from tortoise.expressions import Q
from tortoise.fields import ManyToManyRelation
from tortoise.queryset import QuerySet
from tortoise.transactions import in_transaction
from fastapi import BackgroundTasks

from ex_fastapi import CamelModel
from ex_fastapi.routers.base_crud_service import BaseCRUDService, PK, Handler
from ex_fastapi.routers.exceptions import ItemNotFound, NotUnique
from ex_fastapi.routers.filters import BaseFilter
from . import BaseModel
from .auth_dependencies import user_with_perms


TORTOISE_MODEL = TypeVar('TORTOISE_MODEL', bound=BaseModel)


class TortoiseCRUDService(BaseCRUDService[PK, TORTOISE_MODEL]):
    model: Type[TORTOISE_MODEL]
    queryset_select_related: Sequence[str]
    queryset_prefetch_related: Sequence[str]
    queryset_default_filters: dict[str, Any]

    create_handlers: dict[Type[TORTOISE_MODEL], Handler]
    edit_handlers: dict[Type[TORTOISE_MODEL], Handler]

    def __init__(
            self,
            db_model: Type[TORTOISE_MODEL],
            *,
            read_schema: Type[CamelModel] = None,
            read_list_item_schema: Type[CamelModel] = None,
            create_schema: Type[CamelModel] = None,
            edit_schema: Type[CamelModel] = None,
            queryset_select_related: Sequence[str] = None,
            queryset_prefetch_related: Sequence[str] = None,
            queryset_default_filters: dict[str, Any] = None,
            node_key: str = 'parent_id',
            create_handlers: dict[Type[TORTOISE_MODEL], Handler] = None,
            edit_handlers: dict[Type[TORTOISE_MODEL], Handler] = None,
    ):
        super().__init__(db_model)  # чтобы не ругался
        self.model = db_model
        self.pk_field_type = self.model._meta.pk.field_type
        self._pk = self.model._meta.pk_attr

        self.read_schema = read_schema
        self.list_item_schema = read_list_item_schema or self.read_schema
        self.create_schema = create_schema
        self.edit_schema = edit_schema

        self.queryset_select_related = queryset_select_related or ()
        self.queryset_prefetch_related = queryset_prefetch_related or ()
        self.queryset_default_filters = queryset_default_filters or ()
        self._queryset = None

        self.node_key = node_key

        self.create_handlers = create_handlers or {}
        self.edit_handlers = edit_handlers or {}

    def get_queryset(self) -> QuerySet[TORTOISE_MODEL]:
        if self._queryset is None:
            query = self.model.all()
            if self.queryset_default_filters:
                query = query.filter(**self.queryset_default_filters)
            if self.queryset_select_related:
                query = query.select_related(*self.queryset_select_related)
            if self.queryset_prefetch_related:
                query = query.prefetch_related(*self.queryset_prefetch_related)
            self._queryset = query
        return self._queryset

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: list[str],
            filters: list[BaseFilter],
            background_tasks: BackgroundTasks,
    ) -> tuple[list[TORTOISE_MODEL], int]:
        query = self.get_queryset()
        if sort:
            query = query.order_by(*sort)
        if skip:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)
        for f in filters:
            query = f.filter(query)
        async with in_transaction():
            result = await query
            count = await query.count()
        return result, count

    def _get_many_queryset(self, item_ids: list[PK], *args: Q, **kwargs) -> QuerySet[TORTOISE_MODEL]:
        return self.get_queryset().filter(*args, **{'pk__in': item_ids, **kwargs})

    async def get_many(
            self,
            item_ids: list[PK],
            background_tasks: BackgroundTasks,
            **kwargs
    ) -> list[TORTOISE_MODEL]:
        return await self._get_many_queryset(item_ids)

    async def get_one(
            self,
            item_id: PK,
            background_tasks: BackgroundTasks,
            *args: Q,
            **kwargs
    ) -> Optional[TORTOISE_MODEL]:
        instance = await self.get_queryset().get_or_none(*args, **{'pk': item_id, **kwargs})
        if instance is None:
            raise ItemNotFound()
        return instance

    async def get_tree_node(
            self,
            node_id: Optional[PK],
            background_tasks: BackgroundTasks,
            *args: Q, **kwargs
    ) -> list[TORTOISE_MODEL]:
        return await self.get_queryset().filter(*args, **{self.node_key: node_id, **kwargs})

    async def create(
            self,
            data: CamelModel,
            *,
            exclude: set[str] = None,
            check_unique: bool = True,
            model: Type[TORTOISE_MODEL] = None,
            background_tasks: BackgroundTasks = None,
            **kwargs
    ) -> TORTOISE_MODEL:
        # TODO: придумать что делать с fk fields
        model: Type[TORTOISE_MODEL] = model or self.model
        fk_fields, o2o_fields = exclude_fk_and_o2o(model, data)
        m2m_fields = exclude_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *o2o_fields, *m2m_fields}

        async with in_transaction():
            not_unique = []
            if check_unique:
                not_unique.extend(await model.check_unique(data.dict(exclude=should_exclude)))
            instance: TORTOISE_MODEL = await self.handle_create(model)(
                data, should_exclude=should_exclude, **kwargs
            )
            if o2o_fields:
                try:
                    await self.create_o2o(instance, o2o_fields, data, exclude_dict, check_unique=check_unique)
                except NotUnique as e:
                    not_unique.extend(e.fields)
            if not_unique:
                raise NotUnique(fields=not_unique)
            await self.save_m2m(instance, data, m2m_fields=m2m_fields, clear=False)

        return instance

    async def create_o2o(
            self,
            instance: TORTOISE_MODEL,
            o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
            check_unique=True,
    ):
        not_unique = []
        for field_name in o2o_fields:
            o2o_data = getattr(data, field_name)
            o2o_model = instance.__class__._meta.fields_map[field_name].related_model
            o2o_exclude = exclude_dict[field_name]
            try:
                o2o_instance = await self.create(
                    o2o_data, exclude=o2o_exclude, check_unique=check_unique, model=o2o_model
                )
                setattr(instance, field_name, o2o_instance)
            except NotUnique as e:
                not_unique.extend([f'{field_name}.{f}' for f in e.fields])
        if not_unique:
            raise NotUnique(fields=not_unique)
        await instance.save(force_update=True)

    async def edit(
            self,
            item_id_or_instance: PK | TORTOISE_MODEL,
            data: CamelModel,
            *args: Q,
            exclude: set[str] = None,
            check_unique: bool = True,
            background_tasks: BackgroundTasks = None,
            **kwargs
    ) -> TORTOISE_MODEL:
        # TODO: придумать что делать с fk fields
        model: Type[TORTOISE_MODEL]
        if isinstance(item_id_or_instance, BaseModel):
            model = item_id_or_instance.__class__
        else:
            model = self.model
        fk_fields, o2o_fields = exclude_fk_and_o2o(model, data)
        m2m_fields = exclude_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *o2o_fields, *m2m_fields}
        if isinstance(item_id_or_instance, BaseModel):
            instance = item_id_or_instance
        else:
            instance = await self.get_one(item_id=item_id_or_instance, *args)

        async with in_transaction():
            not_unique = []
            if check_unique:
                not_unique.extend(await model.check_unique(data.dict(exclude=should_exclude, exclude_unset=True)))
            await self.handle_edit(instance)(data, should_exclude=should_exclude, **kwargs)
            if o2o_fields:
                try:
                    await self.edit_o2o(instance, o2o_fields, data, exclude_dict, check_unique)
                except NotUnique as e:
                    not_unique.extend(e.fields)
            if not_unique:
                raise NotUnique(fields=not_unique)
            await self.save_m2m(instance, data, m2m_fields=m2m_fields)
        return instance

    async def edit_o2o(
            self,
            instance: TORTOISE_MODEL,
            o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
            check_unique: bool,
    ):
        not_unique = []
        for field_name in o2o_fields:
            o2o_instance = getattr(instance, field_name)
            o2o_data = getattr(data, field_name)
            o2o_exclude = exclude_dict[field_name]
            try:
                await self.edit(o2o_instance, o2o_data, exclude=o2o_exclude, check_unique=check_unique)
            except NotUnique as e:
                not_unique.extend([f'{field_name}.{f}' for f in e.fields])
        if not_unique:
            raise NotUnique(fields=not_unique)

    async def delete_many(self, item_ids: list[PK], background_tasks: BackgroundTasks, *args: Q, **kwargs) -> int:
        return await self._get_many_queryset(item_ids, *args, **kwargs).delete()

    async def delete_one(self, item_id: PK, background_tasks: BackgroundTasks, **kwargs) -> None:
        item = await self.get_one(item_id, background_tasks=background_tasks, **kwargs)
        await item.delete()

    def handle_create(self, model: Type[TORTOISE_MODEL]) -> Handler:
        if handler := self.create_handlers.get(model):
            return handler

        async def base_handler(
                data: CamelModel,
                should_exclude: set[str] = None,
                **kwargs
        ) -> TORTOISE_MODEL:
            data_dict = data.dict(exclude=should_exclude)
            data_dict.update(kwargs)
            return await model.create(**data_dict)

        self.create_handlers[model] = base_handler
        return base_handler

    def handle_edit(self, instance: TORTOISE_MODEL) -> Handler:
        model = instance.__class__
        if handler := self.edit_handlers.get(model):
            return handler

        async def base_handler(
                data: CamelModel,
                should_exclude: set[str] = None,
                **kwargs
        ) -> TORTOISE_MODEL:
            data_dict = data.dict(exclude=should_exclude, exclude_unset=True)
            data_dict.update(kwargs)
            instance.update_from_dict(data_dict)
            await instance.save(force_update=True)
            return instance

        self.create_handlers[model] = base_handler
        return base_handler

    async def save_m2m(self, instance: TORTOISE_MODEL, data: CamelModel, m2m_fields: set[str], clear=True) -> None:
        if not m2m_fields:
            return
        for field_name in m2m_fields:
            rel: ManyToManyRelation = getattr(instance, field_name)
            ids: list[PK] = getattr(data, field_name)
            if clear:
                await rel.clear()
            await rel.add(*(await rel.remote_model.filter(pk__in=ids)))
        await instance.fetch_related(*m2m_fields)

    def has_create_permissions(self):
        return user_with_perms((self.model, 'create'))

    def has_get_permissions(self):
        return user_with_perms((self.model, 'get'))

    def has_edit_permissions(self):
        return user_with_perms((self.model, 'edit'))

    def has_delete_permissions(self):
        return user_with_perms((self.model, 'delete'))


def get_exclude_dict(fields: set[str]) -> dict[str, set[str]]:
    """
    Из {a, b, c.d, c.e, f.g.h, f.g.i} делает
    {
        '__root__': {'a', 'b'},
        'c': {'d', 'e'},
        'f': {'g.h', 'g.i'}
    }
    """
    exclude_dict = defaultdict(set)
    for field in fields:
        if '.' not in field:
            exclude_dict['__root__'].add(field)
        else:
            base, _, field_in_related = field.partition('.')
            exclude_dict[base].add(field_in_related)
    return exclude_dict


def exclude_fk_and_o2o(model: Type[BaseModel], data: CamelModel) -> tuple[set[str], set[str]]:
    opts = model._meta
    return (
        exclude_fields_from_data(data, *opts.fk_fields),
        exclude_fields_from_data(data, *opts.o2o_fields)
    )


def exclude_m2m(model: Type[BaseModel], data: CamelModel) -> set[str]:
    return exclude_fields_from_data(data, *model._meta.m2m_fields)


def exclude_fields_from_data(data: CamelModel, *fields: str) -> set[str]:
    return_fields: set[str] = set()
    for field_name in fields:
        if getattr(data, field_name, None) is not None:
            return_fields.add(field_name)
    return return_fields

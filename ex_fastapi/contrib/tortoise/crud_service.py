from collections import defaultdict
from collections.abc import Sequence, Callable, Coroutine
from typing import Type, Any, Optional, TypeVar
from typing_extensions import Protocol

from tortoise.expressions import Q
from tortoise.fields import ManyToManyRelation
from tortoise.queryset import QuerySet
from tortoise.transactions import in_transaction

from . import Model
from ex_fastapi.routers.base_crud_service import BaseCRUDService, PK, SCHEMA
from ex_fastapi.routers.exceptions import ItemNotFound, NotUnique

TORTOISE_MODEL = TypeVar('TORTOISE_MODEL', bound=Model)


class Handler(Protocol):
    async def __call__(self, data: SCHEMA, should_exclude: set[str], **kwargs) -> Model: ...


class TortoiseCRUDService(BaseCRUDService[PK, TORTOISE_MODEL]):
    model: Type[TORTOISE_MODEL]
    queryset_select_related: Sequence[str]
    queryset_prefetch_related: Sequence[str]
    queryset_default_filters: dict[str, Any]

    create_handlers: dict[Type[Model], Handler]
    edit_handlers: dict[Type[Model], Handler]

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
            node_key: str = 'parent_id',
            create_handlers: dict[Type[Model], Handler] = None,
            edit_handlers: dict[Type[Model], Handler] = None,
            **kwargs,
    ):
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

        super().__init__(**kwargs)

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
            # filters:
            *args: Q,
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
        if args or kwargs:
            query = query.filter(*args, **kwargs)
        async with in_transaction():
            result = await query
            count = await total_query
        return result, count

    def _get_many_queryset(self, item_ids: list[PK], *args: Q, **kwargs) -> QuerySet[TORTOISE_MODEL]:
        return self.get_queryset().filter(*args, **{'pk__in': item_ids, **kwargs})

    async def get_many(self, item_ids: list[PK], **kwargs) -> list[TORTOISE_MODEL]:
        return await self._get_many_queryset(item_ids)

    async def get_one(self, item_id: PK, *args: Q, **kwargs) -> Optional[TORTOISE_MODEL]:
        instance = await self.get_queryset().get_or_none(*args, **{'pk': item_id, **kwargs})
        if instance is None:
            raise ItemNotFound()
        return instance

    async def get_tree_node(self, node_id: Optional[PK], *args: Q, **kwargs) -> list[TORTOISE_MODEL]:
        return await self.get_queryset().filter(*args, **{self.node_key: node_id, **kwargs})

    async def create(
            self,
            data: SCHEMA,
            *,
            exclude: set[str] = None,
            check_unique: bool = True,
            model: Type[Model] = None,
            **kwargs
    ) -> TORTOISE_MODEL:
        model: Type[Model] = model or self.model
        fk_fields = self.exclude_fk(model, data)
        m2m_fields = self.exclude_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *m2m_fields}
        instance: Model = await self.handle_create(model)(data, should_exclude, **kwargs)

        async with in_transaction():
            not_unique = []
            try:
                await self.create_fk(instance, fk_fields, data, exclude_dict, check_unique=check_unique)
            except NotUnique as e:
                not_unique.extend(e.fields)
            if check_unique:
                not_unique.extend(await model.check_unique(data.dict(exclude=should_exclude)))
            if not_unique:
                raise NotUnique(fields=not_unique)
            await instance.save(force_create=True)
            await self.save_m2m(instance, data, m2m_fields=m2m_fields, clear=False)

        return instance

    async def create_fk(
            self,
            instance: TORTOISE_MODEL,
            fk_fields: set[str],
            data: SCHEMA,
            exclude_dict: dict[str, set[str]],
            check_unique=True,
    ):
        not_unique = []
        for field_name in fk_fields:
            fk_data = getattr(data, field_name)
            fk_model = instance.__class__._meta.fields_map[field_name].related_model
            fk_exclude = exclude_dict[field_name]
            try:
                fk_instance = await self.create(fk_data, exclude=fk_exclude, check_unique=check_unique, model=fk_model)
                setattr(instance, field_name, fk_instance)
            except NotUnique as e:
                not_unique.extend([f'{field_name}.{f}' for f in e.fields])
        if not_unique:
            raise NotUnique(fields=not_unique)

    async def edit(
            self,
            item_id_or_instance: PK | TORTOISE_MODEL,
            data: SCHEMA,
            *args: Q,
            exclude: set[str] = None,
            check_unique: bool = True,
            **kwargs
    ) -> TORTOISE_MODEL:
        model: Type[Model]
        if isinstance(item_id_or_instance, Model):
            model = item_id_or_instance.__class__
        else:
            model = self.model
        fk_fields = self.exclude_fk(model, data)
        m2m_fields = self.exclude_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *m2m_fields}
        if isinstance(item_id_or_instance, Model):
            instance = item_id_or_instance
        else:
            instance = await self.get_one(item_id_or_instance, *args)
        instance = await self.handle_edit(instance)(data, should_exclude, **kwargs)

        async with in_transaction():
            not_unique = []
            try:
                await self.edit_fk(instance, fk_fields, data, exclude_dict, check_unique)
            except NotUnique as e:
                not_unique.extend(e.fields)
            if check_unique:
                not_unique.extend(await model.check_unique(data.dict(exclude=should_exclude, exclude_unset=True)))
            if not_unique:
                raise NotUnique(fields=not_unique)
            await instance.save(force_update=True)
            await self.save_m2m(instance, data, m2m_fields=m2m_fields)
        return instance

    async def edit_fk(
            self,
            instance: TORTOISE_MODEL,
            fk_fields: set[str],
            data: SCHEMA,
            exclude_dict: dict[str, set[str]],
            check_unique: bool,
    ):
        not_unique = []
        for field_name in fk_fields:
            fk_instance = getattr(instance, field_name)
            fk_data = getattr(data, field_name)
            fk_exclude = exclude_dict[field_name]
            try:
                await self.edit(fk_instance, fk_data, exclude=fk_exclude, check_unique=check_unique)
            except NotUnique as e:
                not_unique.extend([f'{field_name}.{f}' for f in e.fields])
        if not_unique:
            raise NotUnique(fields=not_unique)

    async def delete_many(self, item_ids: list[PK], *args: Q, **kwargs) -> int:
        return await self._get_many_queryset(item_ids, *args, **kwargs).delete()

    async def delete_one(self, item_id: PK, *args: Q, **kwargs) -> None:
        item = await self.get_one(item_id, *args, **kwargs)
        await item.delete()

    def exclude_fk(self, model: Type[Model], data: SCHEMA) -> set[str]:
        opts = model._meta
        return self.exclude_fields_from_data(data, *opts.fk_fields, *opts.o2o_fields)

    def exclude_m2m(self, model: Type[Model], data: SCHEMA) -> set[str]:
        return self.exclude_fields_from_data(data, *model._meta.m2m_fields)

    def handle_create(self, model: Type[Model]) -> Handler:
        if handler := self.create_handlers.get(model):
            return handler

        async def base_handler(data: SCHEMA, should_exclude: set[str], **kwargs) -> Model:
            data_dict = data.dict(exclude=should_exclude)
            data_dict.update(kwargs)
            return model(**data_dict)

        self.create_handlers[model] = base_handler
        return base_handler

    def handle_edit(self, instance: Model) -> Handler:
        model = instance.__class__
        if handler := self.edit_handlers.get(model):
            return handler

        async def base_handler(data: SCHEMA, should_exclude: set[str], **kwargs) -> Model:
            data_dict = data.dict(exclude=should_exclude, exclude_unset=True)
            data_dict.update(kwargs)
            return instance.update_from_dict(data_dict)

        self.create_handlers[model] = base_handler
        return base_handler

    @classmethod
    def exclude_fields_from_data(cls, data: SCHEMA, *fields: str) -> set[str]:
        m2m_fields: set[str] = set()
        for field_name in fields:
            if getattr(data, field_name, None) is not None:
                m2m_fields.add(field_name)
        return m2m_fields

    async def save_m2m(self, instance: TORTOISE_MODEL, data: SCHEMA, m2m_fields: set[str], clear=True) -> None:
        if not m2m_fields:
            return
        for field_name in m2m_fields:
            rel: ManyToManyRelation = getattr(instance, field_name)
            ids: list[PK] = getattr(data, field_name)
            if clear:
                await rel.clear()
            await rel.add(*(await rel.remote_model.filter(pk__in=ids)))
        await instance.fetch_related(*self.queryset_prefetch_related)


def get_exclude_dict(fields: set[str]) -> dict[str, set[str]]:
    exclude_dict = defaultdict(set)
    for field in fields:
        if '.' not in field:
            exclude_dict['__root__'].add(field)
        else:
            base, _, field_in_related = field.partition('.')
            exclude_dict[base].add(field_in_related)
    return exclude_dict

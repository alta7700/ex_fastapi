from collections import defaultdict
from functools import lru_cache
from typing import Type, Any, Optional, TypeVar, Sequence

from tortoise.fields import ManyToManyRelation
from tortoise.models import MetaInfo
from tortoise.queryset import QuerySet
from tortoise.transactions import in_transaction
from fastapi import BackgroundTasks, Request

from ex_fastapi import CamelModel
from ex_fastapi.routers.base_crud_service import BaseCRUDService, PK, Handler, QsRelatedFunc
from ex_fastapi.routers.exceptions import ItemNotFound, NotUnique, NotFoundFK, MultipleFieldsError
from ex_fastapi.routers.filters import BaseFilter
from . import BaseModel


TORTOISE_MODEL = TypeVar('TORTOISE_MODEL', bound=BaseModel)


class TortoiseCRUDService(BaseCRUDService[PK, TORTOISE_MODEL]):
    model: Type[TORTOISE_MODEL]
    opts: MetaInfo

    def __init__(
            self,
            db_model: Type[TORTOISE_MODEL],
            *,
            read_schema: Type[CamelModel] = None,
            read_list_item_schema: Type[CamelModel] = None,
            create_schema: Type[CamelModel] = None,
            edit_schema: Type[CamelModel] = None,
            queryset_select_related: QsRelatedFunc | set[str] = None,
            queryset_prefetch_related: QsRelatedFunc | set[str] = None,
            queryset_default_filters: dict[str, Any] = None,
            node_key: str = 'parent_id',
            create_handlers: dict[Type[TORTOISE_MODEL], Handler] = None,
            edit_handlers: dict[Type[TORTOISE_MODEL], Handler] = None,
    ):
        super().__init__(db_model)  # чтобы не ругался
        self.model = db_model
        self.opts = self.model._meta
        self.pk_field_type = self.opts.pk.field_type  # type: ignore
        self._pk = self.opts.pk_attr

        self.read_schema = read_schema
        self.list_item_schema = read_list_item_schema or self.read_schema
        self.create_schema = create_schema
        self.edit_schema = edit_schema

        if queryset_select_related is None:
            self.queryset_select_related = self.model.get_queryset_select_related
        else:
            if callable(queryset_select_related):
                self.queryset_select_related = queryset_select_related
            else:
                self.queryset_select_related = lambda path, method: queryset_select_related
        if queryset_prefetch_related is None:
            self.queryset_prefetch_related = self.model.get_queryset_prefetch_related
        else:
            if callable(queryset_prefetch_related):
                self.queryset_prefetch_related = queryset_prefetch_related
            else:
                self.queryset_prefetch_related = lambda path, method: queryset_prefetch_related
        self.queryset_default_filters = queryset_default_filters or ()

        self.node_key = node_key

        self.create_handlers = create_handlers or {}
        self.edit_handlers = edit_handlers or {}

    @lru_cache
    def _get_queryset(
            self,
            path: str,
            method: str,
            select_related: str,
            prefetch_related: str,
    ) -> QuerySet[TORTOISE_MODEL]:
        query = self.model.all()
        select_related = select_related.split(',') if select_related else ()
        prefetch_related = prefetch_related.split(',') if select_related else ()
        if self.queryset_default_filters:
            query = query.filter(**self.queryset_default_filters)
        if self.queryset_select_related:
            query = query.select_related(*{*self.queryset_select_related(path, method), *select_related})
        if self.queryset_prefetch_related:
            query = query.prefetch_related(*{*self.queryset_prefetch_related(path, method), *prefetch_related})
        return query

    def get_queryset(
            self,
            request: Request,
            select_related: Sequence[str],
            prefetch_related: Sequence[str],
    ) -> QuerySet[TORTOISE_MODEL]:
        if request is None:
            path, method = '', ''
        else:
            path, method = request.scope['route'].path, request.method
        # select_related и prefetch_related переводим в строку с запятыми, чтобы lru_cache работал как хотим
        select_related, prefetch_related = ','.join(select_related), ','.join(prefetch_related)
        return self._get_queryset(path, method, select_related, prefetch_related)

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: list[str],
            filters: list[BaseFilter],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> tuple[list[TORTOISE_MODEL], int]:
        query = self.get_queryset(request, select_related, prefetch_related)
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

    def _get_many_queryset(
            self,
            item_ids: list[PK],
            *,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> QuerySet[TORTOISE_MODEL]:
        return self.get_queryset(
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related
        ).filter(pk__in=item_ids)

    async def get_many(
            self,
            item_ids: list[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> list[TORTOISE_MODEL]:
        return await self._get_many_queryset(
            item_ids,
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related
        )

    async def get_one(
            self,
            item_id: PK,
            *,
            field_name: str = 'pk',
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> Optional[TORTOISE_MODEL]:
        instance = await self.get_queryset(
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related,
        ).get_or_none(**{field_name: item_id})
        if instance is None:
            raise ItemNotFound()
        return instance

    async def get_tree_node(
            self,
            node_id: Optional[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> list[TORTOISE_MODEL]:
        return await self.get_queryset(
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related,
        ).filter(**{self.node_key: node_id})

    async def create(
            self,
            data: CamelModel,
            *,
            exclude: set[str] = None,
            model: Type[TORTOISE_MODEL] = None,
            background_tasks: BackgroundTasks = None,
            defaults: dict[str, Any] = None,
            request: Request = None,
    ) -> TORTOISE_MODEL:
        model: Type[TORTOISE_MODEL] = model or self.model
        fk_fields, bfk_fields, o2o_fields, bo2o_fields, m2m_fields = exclude_fk_o2o_bo2o_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *bfk_fields, *o2o_fields, *bo2o_fields, *m2m_fields}
        errors = MultipleFieldsError()

        async with in_transaction():
            not_unique = await model.check_unique(data.dict(exclude=should_exclude))
            if not_unique:
                errors.add_errors(NotUnique(fields=not_unique))
                raise errors
            instance: TORTOISE_MODEL = await self.handle_create(model)(
                data, should_exclude=should_exclude, defaults=defaults
            )
            if o2o_fields:
                try:
                    await self.create_o2o(instance, o2o_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if bo2o_fields:
                try:
                    await self.create_backward_o2o(instance, bo2o_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if fk_fields:
                try:
                    await self.set_fk(instance, fk_fields, data)
                except NotFoundFK as e:
                    errors.add_errors(e)
            if bfk_fields:
                try:
                    await self.create_backward_fk(instance, bfk_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if errors:
                raise errors
            await self.save_m2m(instance, data, m2m_fields=m2m_fields, clear=False)

        return await self.get_one(instance.pk, request=request)

    async def create_o2o(
            self,
            instance: TORTOISE_MODEL,
            o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ) -> None:
        errors = MultipleFieldsError()
        for field_name in o2o_fields:
            o2o_data = getattr(data, field_name)
            if o2o_data is None:
                continue
            o2o_model: Type[TORTOISE_MODEL] = instance._meta.fields_map[field_name].related_model
            o2o_exclude = exclude_dict[field_name]
            try:
                o2o_instance = await self.create(o2o_data, exclude=o2o_exclude, model=o2o_model)
                setattr(instance, field_name, o2o_instance)
            except MultipleFieldsError as e:
                errors.add_errors(*e.with_prefix(field_name))
        if errors:
            raise errors
        await instance.save(force_update=True, update_fields=o2o_fields)

    async def create_backward_o2o(
            self,
            instance: TORTOISE_MODEL,
            back_o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ) -> None:
        errors = MultipleFieldsError()
        for field_name in back_o2o_fields:
            back_o2o_data = getattr(data, field_name)
            if back_o2o_data is None:
                continue
            back_o2o_field = instance._meta.fields_map[field_name]
            back_o2o_model: Type[TORTOISE_MODEL] = back_o2o_field.related_model
            back_o2o_source_field = back_o2o_model._meta\
                .fields_map[back_o2o_field.relation_source_field]\
                .reference.model_field_name
            back_o2o_exclude = exclude_dict[field_name]
            try:
                await self.create(
                    back_o2o_data, exclude=back_o2o_exclude, model=back_o2o_model,
                    defaults={back_o2o_source_field: instance}
                )
            except MultipleFieldsError as e:
                errors.add_errors(*e.with_prefix(field_name))
        if errors:
            raise errors
        await instance.fetch_related(*back_o2o_fields)

    async def create_backward_fk(
            self,
            instance: TORTOISE_MODEL,
            back_fk_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ) -> None:
        errors = MultipleFieldsError()
        for field_name in back_fk_fields:
            back_fk_field = instance._meta.fields_map[field_name]
            back_fk_model: Type[TORTOISE_MODEL] = back_fk_field.related_model
            back_fk_source_field = back_fk_model._meta \
                .fields_map[back_fk_field.relation_source_field] \
                .reference.model_field_name
            back_fk_exclude = exclude_dict[field_name]
            for back_fk_data in getattr(data, field_name):
                try:
                    await self.create(
                        back_fk_data, exclude=back_fk_exclude, model=back_fk_model,
                        defaults={back_fk_source_field: instance}
                    )
                except MultipleFieldsError as e:
                    errors.add_errors(*e.with_prefix(field_name))
        if errors:
            raise errors
        await instance.fetch_related(*back_fk_fields)

    async def edit(
            self,
            item_id_or_instance: PK | TORTOISE_MODEL,
            data: CamelModel,
            *,
            exclude: set[str] = None,
            background_tasks: BackgroundTasks = None,
            defaults: dict[str, Any] = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> TORTOISE_MODEL:
        model: Type[TORTOISE_MODEL] = item_id_or_instance.__class__ if isinstance(item_id_or_instance, BaseModel) \
            else self.model
        fk_fields, bfk_fields, o2o_fields, bo2o_fields, m2m_fields = exclude_fk_o2o_bo2o_m2m(model, data)
        exclude_dict = get_exclude_dict(exclude or set())
        should_exclude = {*exclude_dict['__root__'], *fk_fields, *bfk_fields, *o2o_fields, *bo2o_fields, *m2m_fields}
        if isinstance(item_id_or_instance, BaseModel):
            instance = item_id_or_instance
        else:
            instance = await self.get_one(
                item_id_or_instance,
                background_tasks=background_tasks,
                request=request,
                select_related=select_related,
                prefetch_related=prefetch_related
            )
        errors = MultipleFieldsError()

        async with in_transaction():
            if not_unique := await model.check_unique(data.dict(exclude=should_exclude, exclude_unset=True)):
                errors.add_errors(NotUnique(fields=not_unique))
            await self.handle_edit(instance)(data, should_exclude=should_exclude, defaults=defaults)
            if o2o_fields:
                try:
                    await self.edit_o2o(instance, o2o_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if bo2o_fields:
                try:
                    await self.edit_backward_o2o(instance, bo2o_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if fk_fields:
                try:
                    await self.set_fk(instance, fk_fields, data)
                except NotFoundFK as e:
                    errors.add_errors(e)
            if bfk_fields:
                try:
                    await self.edit_backward_fk(instance, bfk_fields, data, exclude_dict)
                except MultipleFieldsError as e:
                    errors.add_errors(*e)
            if errors:
                raise errors
            await self.save_m2m(instance, data, m2m_fields=m2m_fields)
        return instance

    async def edit_o2o(
            self,
            instance: TORTOISE_MODEL,
            o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ) -> None:
        errors = MultipleFieldsError()
        need_refetch: set[str] = set()
        for field_name in o2o_fields:
            o2o_instance = getattr(instance, field_name)
            o2o_data = getattr(data, field_name)
            o2o_exclude = exclude_dict[field_name]
            try:
                if o2o_instance is not None:
                    await self.edit(o2o_instance, o2o_data, exclude=o2o_exclude)
                else:
                    o2o_model: Type[TORTOISE_MODEL] = instance._meta.fields_map[field_name].related_model
                    await self.create(o2o_data, exclude=o2o_exclude, model=o2o_model)
                    need_refetch.add(field_name)
            except MultipleFieldsError as e:
                errors.add_errors(*e.with_prefix(field_name))
        if errors:
            raise errors
        if need_refetch:
            await instance.fetch_related(*need_refetch)

    async def edit_backward_o2o(
            self,
            instance: TORTOISE_MODEL,
            backward_o2o_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ):
        errors = MultipleFieldsError()
        need_refetch: set[str] = set()
        for field_name in backward_o2o_fields:
            back_o2o_instance = getattr(instance, field_name)
            back_o2o_data = getattr(data, field_name)
            back_o2o_exclude = exclude_dict[field_name]
            back_o2o_field = instance._meta.fields_map[field_name]
            back_o2o_model: Type[TORTOISE_MODEL] = back_o2o_field.related_model
            back_o2o_source_field = back_o2o_model._meta \
                .fields_map[back_o2o_field.relation_source_field] \
                .reference.model_field_name
            try:
                if back_o2o_instance is not None:
                    await self.edit(back_o2o_instance, back_o2o_data, exclude=back_o2o_exclude)
                else:
                    await self.create(
                        back_o2o_data, exclude=back_o2o_exclude, model=back_o2o_model,
                        defaults={back_o2o_source_field: instance}
                    )
                    need_refetch.add(field_name)
            except MultipleFieldsError as e:
                errors.add_errors(*e.with_prefix(field_name))
        if errors:
            raise errors
        if need_refetch:
            await instance.fetch_related(*need_refetch)

    async def edit_backward_fk(
            self,
            instance: TORTOISE_MODEL,
            backward_fk_fields: set[str],
            data: CamelModel,
            exclude_dict: dict[str, set[str]],
    ):
        def get_fk_instance(instances: list[TORTOISE_MODEL], pk_value) -> TORTOISE_MODEL | None:
            for i in instances:
                if i.pk == pk_value:
                    return i

        not_found_fk: set[str] = set()
        errors = MultipleFieldsError()
        need_refetch: set[str] = set()
        for field_name in backward_fk_fields:
            back_fk_instances: list[TORTOISE_MODEL] = getattr(instance, field_name)
            back_fk_field = instance._meta.fields_map[field_name]
            back_fk_model: Type[TORTOISE_MODEL] = back_fk_field.related_model
            back_fk_source_field = back_fk_model._meta \
                .fields_map[back_fk_field.relation_source_field] \
                .reference.model_field_name
            back_pk_attr = back_fk_model._meta.pk_attr
            back_o2o_exclude = exclude_dict[field_name]
            for back_fk_data in getattr(data, field_name):
                pk = getattr(back_fk_data, back_pk_attr, None)
                try:
                    if pk:
                        fk_instance = get_fk_instance(back_fk_instances, pk)
                        if not fk_instance:
                            not_found_fk.add(field_name)
                        else:
                            await self.edit(fk_instance, back_fk_data, exclude=back_o2o_exclude)
                    else:
                        await self.create(
                            back_fk_data, exclude=back_o2o_exclude, model=back_fk_model,
                            defaults={back_fk_source_field: instance}
                        )
                        need_refetch.add(field_name)
                except MultipleFieldsError as e:
                    errors.add_errors(*e.with_prefix(field_name))
        if not_found_fk:
            errors.add_errors(NotFoundFK(fields=not_found_fk))
        if errors:
            raise errors
        if need_refetch:
            await instance.fetch_related(*need_refetch)

    async def set_fk(
            self,
            instance: TORTOISE_MODEL,
            fk_fields: set[str],
            data: CamelModel,
            not_found_fk: set[str] = None
    ) -> None:
        opts = instance._meta
        fk_fields_map: dict[str, tuple[Type[TORTOISE_MODEL], str]] = {
            (f_opts := opts.fields_map[f]).source_field: (f_opts.related_model, f) for f in opts.fk_fields
        }
        not_found_fk: set[str] = not_found_fk or set()
        for source_field_name in fk_fields:
            value = getattr(data, source_field_name)
            rel_model, field_name = fk_fields_map[source_field_name]
            rel_instance = await rel_model.get_or_none(pk=value)
            if rel_instance is None:
                not_found_fk.add(source_field_name)
            else:
                setattr(instance, field_name, rel_instance)
        if not_found_fk:
            raise NotFoundFK(fields=not_found_fk)
        await instance.save(force_update=True)

    async def delete_many(
            self,
            item_ids: list[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> int:
        return await self._get_many_queryset(
            item_ids,
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related,
        ).delete()

    async def delete_one(
            self,
            item_id: PK,
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> None:
        item = await self.get_one(
            item_id,
            background_tasks=background_tasks,
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related,
        )
        await item.delete()

    def handle_create(self, model: Type[TORTOISE_MODEL]) -> Handler:
        if handler := self.create_handlers.get(model):
            return handler

        async def base_handler(
                data: CamelModel,
                should_exclude: set[str] = None,
                defaults: dict[str, Any] = None,
        ) -> TORTOISE_MODEL:
            data_dict = data.dict(exclude=should_exclude)
            data_dict.update(defaults or {})
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
                defaults: dict[str, Any] = None,
        ) -> TORTOISE_MODEL:
            data_dict = data.dict(exclude=should_exclude, exclude_unset=True)
            data_dict.update(defaults or {})
            instance.update_from_dict(data_dict)
            await instance.save(force_update=True)
            return instance

        self.edit_handlers[model] = base_handler
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


def exclude_fk_o2o_bo2o_m2m(
        model: Type[BaseModel], data: CamelModel
) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    opts = model._meta
    return (
        exclude_fields_from_data(data, *(opts.fields_map[f].source_field for f in opts.fk_fields)),
        exclude_fields_from_data(data, *opts.backward_fk_fields),
        exclude_fields_from_data(data, *opts.o2o_fields),
        exclude_fields_from_data(data, *opts.backward_o2o_fields),
        exclude_fields_from_data(data, *opts.m2m_fields)
    )


def exclude_fields_from_data(data: CamelModel, *fields: str) -> set[str]:
    return_fields: set[str] = set()
    for field_name in fields:
        if field_name in data.__fields_set__:
            return_fields.add(field_name)
    return return_fields

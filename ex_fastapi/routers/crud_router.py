from collections.abc import Sequence
from enum import Enum
from typing import Callable, Any, Generic, TypeVar, Optional, Literal, Type

from fastapi import Response, Request, APIRouter, Body, Path, Query, params, Depends, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper

from ex_fastapi import BaseCodes, snake_case, CommaSeparatedOf, lower_camel
from ex_fastapi.global_objects import get_default_codes
from ex_fastapi.default_response import BgHTTPException
from . import BaseCRUDService
from .exceptions import NotUnique, ItemNotFound
from .filters import BaseFilter
from .utils import pagination_factory, PAGINATION


DISPLAY_FIELDS = tuple[str, ...]
SERVICE = TypeVar('SERVICE', bound=BaseCRUDService)
DEPENDENCIES = Optional[Sequence[params.Depends]]
ROUTES_KWARGS = dict[str, bool | dict[str, Any]]

Codes = get_default_codes()


class CRUDRouter(Generic[SERVICE], APIRouter):
    service: SERVICE
    max_items_get_many_routes: Optional[int]
    max_items_delete_many_routes: Optional[int]
    filters: list[Type[BaseFilter]] | bool
    auto_routes_dependencies: DEPENDENCIES

    def __init__(
            self,
            service: SERVICE,
            *,
            max_items_get_many: int = 100,
            max_items_delete_many: int = 100,
            prefix: str = None,
            tags: Optional[list[str | Enum]] = None,
            filters: list[Type[BaseFilter]] | bool = None,
            auto_routes_dependencies: DEPENDENCIES = None,
            routes_kwargs: ROUTES_KWARGS = None,
            add_tree_routes: bool = False,
            read_only: bool = False,
            routes_only: set[str] = None,
            complete_auto_routes: bool = True,
            **kwargs,
    ) -> None:
        """
            :param max_items_get_many         отпределяет маскимальное количество записей, которые достаются по id
            :param max_items_delete_many      отпределяет маскимальное количество записей, которые удаляются по id
            :param prefix                     префикс из APIRouter
            :param tags                       tags из APIRouter
            :param filters                    фильтры для get_all
            :param auto_routes_dependencies   инъекции которые применяются для всех роутов, сгенерированных
                                              автоматически, если нужно для всех, не только автоматически
                                              сгенерированных, то нужно использовать dependencies
            :param routes_kwargs              словарь вида {route_name: add_api_route kwargs},
                                              значение может быть равно False, если этот роут не нужен ({create: False})
            :param add_tree_routes            добавляет методы для деревьев
            :param read_only                  создаёт только get методы
            :param routes_only                set из роутов, которые нужно создать
            :param complete_auto_routes       если нужно создать какие-то роуты, без Path параметров, которые просто так
                                              перекрываются
            :param kwargs                     всё что передаётся в APIRouter
        """

        self.service = service
        prefix = prefix.strip('/') if prefix else self.service.model.__name__.lower() + 's'
        tags = tags or [prefix]
        prefix = '/' + prefix
        super().__init__(prefix=prefix, tags=tags, **kwargs)

        self.max_items_get_many_routes = max_items_get_many
        self.max_items_delete_many_routes = max_items_delete_many
        self.read_only = read_only

        self.auto_routes_dependencies = auto_routes_dependencies or []
        self.routes_kwargs = routes_kwargs or {}

        if routes_only:
            routes_names = routes_only
        else:
            routes_names = self.default_routes_names()
            if add_tree_routes:
                routes_names = *routes_names, *self.tree_route_names()
        self.routes_names = routes_names

        if filters is None:
            filters = []
        self.filters = filters

        if complete_auto_routes:
            self.complete_auto_routes()

    def complete_auto_routes(self) -> None:
        for route_name in self.routes_names:
            route_data = self.routes_kwargs.get(route_name, True)
            if route_data is False:
                continue
            self._register_route(route_name, (route_data if isinstance(route_data, dict) else {}))

    def _get_all_route(self) -> Callable[..., Any]:
        get_all = self.service.get_all
        list_item_schema = self.get_list_item_schema()
        filters = self.filters

        async def route(
                background_tasks: BackgroundTasks,
                response: Response,
                pagination: PAGINATION = pagination_factory(),
                sort: CommaSeparatedOf(str, wrapper=snake_case, in_query=True) = Query(None),
                applied_filters: list[BaseFilter] = Depends(get_filters(filters))
        ):
            raise_if_error_in_filters(applied_filters)
            skip, limit = pagination
            result, total = await get_all(
                skip, limit, sort, filters=applied_filters, background_tasks=background_tasks
            )
            response.headers.append('X-Total-Count', str(total))
            return [list_item_schema.from_orm(r) for r in result]

        return route

    def _get_many_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        max_items = self.max_items_get_many_routes
        get_many = self.service.get_many
        read_schema = self.get_read_schema()

        async def route(
                background_tasks: BackgroundTasks,
                item_ids: CommaSeparatedOf(pk_field_type, max_items=max_items, in_query=True) = Query(..., alias='ids')
        ):
            results = await get_many(item_ids, background_tasks=background_tasks)
            return [read_schema.from_orm(r) for r in results]

        return route

    def _get_one_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        get_one = self.service.get_one
        read_schema = self.get_read_schema()

        async def route(
                background_tasks: BackgroundTasks,
                item_id: pk_field_type = Path(...),
        ):
            try:
                item = await get_one(item_id, background_tasks=background_tasks)
            except ItemNotFound:
                raise self.not_found_error()
            return read_schema.from_orm(item)

        return route

    def _get_tree_node_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        get_tree_node = self.service.get_tree_node
        get_list_item_schema = self.get_list_item_schema()
        alias = lower_camel(self.service.node_key)

        async def route(
                background_tasks: BackgroundTasks,
                node_id: Optional[pk_field_type] = Query(None, alias=alias)
        ):
            return [get_list_item_schema.from_orm(item) for item in await get_tree_node(
                node_id, background_tasks=background_tasks
            )]

        return route

    def _create_route(self) -> Callable[..., Any]:
        create_schema = self.get_create_schema()
        read_schema = self.get_read_schema()
        create = self.service.create

        async def route(
                background_tasks: BackgroundTasks,
                data: create_schema = Body(...)
        ):
            try:
                return read_schema.from_orm(await create(data, background_tasks=background_tasks))
            except NotUnique as e:
                raise self.not_unique_error(e.fields)

        return route

    def _edit_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        read_schema = self.get_read_schema()
        edit_schema = self.get_edit_schema()
        edit = self.service.edit

        async def route(
                background_tasks: BackgroundTasks,
                item_id: pk_field_type = Path(...),
                data: edit_schema = Body(...)
        ):
            try:
                item = await edit(item_id, data, background_tasks=background_tasks)
            except ItemNotFound:
                raise self.not_found_error()
            except NotUnique as e:
                raise self.not_unique_error(e.fields)
            return read_schema.from_orm(item)

        return route

    def _delete_many_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        max_items = self.max_items_get_many_routes
        delete_many = self.service.delete_many

        async def route(
                background_tasks: BackgroundTasks,
                item_ids: CommaSeparatedOf(pk_field_type, max_items=max_items, in_query=True) = Query(..., alias='ids')
        ):
            deleted_items_count = await delete_many(item_ids, background_tasks=background_tasks)
            return self.ok_response(count=deleted_items_count)

        return route

    def _delete_one_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        delete_one = self.service.delete_one

        async def route(
                background_tasks: BackgroundTasks,
                item_id: pk_field_type = Path(...)
        ):
            try:
                await delete_one(item_id, background_tasks=background_tasks)
            except ItemNotFound:
                raise self.not_found_error()
            return self.ok_response(item=item_id)

        return route

    @classmethod
    def _ok_response_instance(cls) -> BaseCodes:
        return Codes.OK

    def ok_response(self, **kwargs) -> dict[str, Any]:
        if kwargs:
            return self._ok_response_instance().resp_detail(**kwargs)
        return self._ok_response_instance().resp

    @classmethod
    def not_found_error_instance(cls) -> BaseCodes:
        return Codes.not_found

    def not_found_error(self) -> BgHTTPException:
        return self.not_found_error_instance().err()

    @classmethod
    def not_unique_error_instance(cls) -> BaseCodes:
        return Codes.not_unique_err

    def not_unique_error(self, fields: list[str]) -> BgHTTPException:
        return self.not_unique_error_instance().format_err(', '.join(fields), {'fields': fields})

    def default_routes_names(self) -> tuple[str, ...]:
        if self.read_only:
            return 'get_all', 'get_many', 'get_one'
        return 'get_all', 'get_many', 'get_one', 'create', 'edit', 'delete_many', 'delete_one'

    @staticmethod
    def tree_route_names() -> tuple[str, ...]:
        return 'get_tree_node',

    def all_route_names(self) -> tuple[str, ...]:
        return *self.default_routes_names(), *self.tree_route_names()

    def _register_route(
            self,
            route_name: str,
            route_kwargs: dict[str, Any],
    ) -> None:
        responses = {}
        response_model = None
        status = 200
        openapi_extra = None
        check_perms = route_kwargs.get('check_perms', True)
        match route_name:
            case 'get_all':
                path = '/all'
                method = ["GET"]
                response_model = list[self.get_list_item_schema()]
                check_perms_dependency = Depends(self.service.has_get_permissions())
                openapi_extra = {'parameters': [f.query_openapi_desc() for f in self.filters]}
            case 'get_many':
                path = '/many'
                method = ["GET"]
                response_model = list[self.get_read_schema()]
                check_perms_dependency = Depends(self.service.has_get_permissions())
            case 'get_one':
                path = '/one/{item_id}'
                method = ["GET"]
                response_model = self.get_read_schema()
                responses = Codes.responses(self.not_found_error_instance())
                check_perms_dependency = Depends(self.service.has_get_permissions())
            case 'get_tree_node':
                path = '/tree'
                method = ["GET"]
                response_model = list[self.get_list_item_schema()]
                check_perms_dependency = Depends(self.service.has_get_permissions())
            case 'create':
                path = ''
                method = ["POST"]
                response_model = self.get_read_schema()
                responses = Codes.responses(
                    (self.not_unique_error_instance(), {'fields': ['поле1', 'поле2']})
                )
                status = 201
                check_perms_dependency = Depends(self.service.has_create_permissions())
            case 'edit':
                path = '/{item_id}'
                method = ["PATCH"]
                response_model = self.get_read_schema()
                responses = Codes.responses(
                    self.not_found_error_instance(),
                    (self.not_unique_error_instance(), {'fields': ['поле1', 'поле2']})
                )
                check_perms_dependency = Depends(self.service.has_edit_permissions())
            case 'delete_many':
                path = '/many'
                method = ["DELETE"]
                # don`t need response model, responses has one with status 200
                responses = Codes.responses((self._ok_response_instance(), {'count': 30}), )
                check_perms_dependency = Depends(self.service.has_delete_permissions())
            case 'delete_one':
                path = '/{item_id}'
                method = ["DELETE"]
                # don`t need response model, responses has one with status 200
                responses = Codes.responses((self._ok_response_instance(), {'item': 77}), )
                check_perms_dependency = Depends(self.service.has_delete_permissions())
            case _:
                raise Exception(f'Unknown name of route: {route_name}.\n'
                                f'Available are {", ".join(self.default_routes_names())}')
        summary = f"{route_name.title().replace('_', ' ')} {self.service.model.__name__}"

        if check_perms:
            dependencies = [*self.auto_routes_dependencies, check_perms_dependency]
        else:
            dependencies = [*self.auto_routes_dependencies]
        route_kwargs = get_route_kwargs(route_kwargs, dependencies, responses)

        self.add_api_route(
            path=path,
            endpoint=getattr(self, f'_{route_name}_route')(),
            methods=method,
            response_model=response_model,
            summary=summary,
            status_code=status,
            openapi_extra=openapi_extra,
            **route_kwargs,
        )

    def get_read_schema(self, generate_if_not_exist: bool = True):
        return self.service.get_read_schema(generate_if_not_exist=generate_if_not_exist)

    def get_list_item_schema(self, generate_if_not_exist: bool = True):
        return self.service.get_list_item_schema(generate_if_not_exist=generate_if_not_exist)

    def get_create_schema(self, generate_if_not_exist: bool = True):
        return self.service.get_create_schema(generate_if_not_exist=generate_if_not_exist)

    def get_edit_schema(self, generate_if_not_exist: bool = True):
        return self.service.get_edit_schema(generate_if_not_exist=generate_if_not_exist)


def get_route_kwargs(
        route_data: dict[str, Any],
        dependencies: DEPENDENCIES,
        responses: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(route_data, bool):
        route_data = {}
    else:
        route_data = {**route_data}
    route_data['dependencies'] = [*dependencies, *route_data.get('dependencies', [])] or None
    route_data['responses'] = {**responses, **route_data.get('responses', {})} or None
    for kwarg in tuple(route_data.keys()):
        if kwarg not in available_api_route_kwargs:
            del route_data[kwarg]
    return route_data


def get_filters(filters: list[Type[BaseFilter]]):
    def wrapper(request: Request) -> list[BaseFilter]:
        qp = request.query_params
        return [final_f for f in filters if (final_f := f.from_qs(qp))]
    return wrapper


def raise_if_error_in_filters(filters: list[BaseFilter]) -> None:
    errors = [ErrorWrapper(f.error, loc=("filters", f.camel_source)) for f in filters if f.error is not None]
    if errors:
        raise RequestValidationError(errors)


available_api_route_kwargs = [
    'dependencies',
    'responses',
    'tags',
    'description',
    'response_description',
    'deprecated',
    'operation_id',
    'response_model_include',
    'response_model_exclude',
    'response_model_by_alias',
    'response_model_exclude_unset',
    'response_model_exclude_defaults',
    'response_model_exclude_none',
    'include_in_schema',
    'response_class',
    'name',
    'route_class_override',
    'callbacks',
    'openapi_extra',
    'generate_unique_id_function',
]

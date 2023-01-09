from collections.abc import Sequence
from enum import Enum
from typing import Callable, Any, Generic, TypeVar, Optional, Type, Literal

from fastapi import Response, APIRouter, Body, Path, Query, params

from ex_fastapi.default_response import BgHTTPException
from ex_fastapi import BaseCodes, snake_case, CommaSeparatedOf
from .base_crud_service import BaseCRUDService, SCHEMA
from .exceptions import NotUnique, ItemNotFound
from .utils import pagination_factory, PAGINATION

DISPLAY_FIELDS = tuple[str, ...]
SERVICE = TypeVar('SERVICE', bound=BaseCRUDService)


class DefaultCodes(BaseCodes):
    OK = 200, 'ОК'
    not_found = 404, 'Не нашёл подходящий элемент :('
    not_unique_err = 400, 'Поле должно быть уникальным ({})'


DEFAULT_ROUTE = Literal['get_all', 'get_many', 'get_one', 'create', 'edit', 'delete_all', 'delete_many', 'delete_one']
TREE_ROUTE = Literal['get_tree_node']
ROUTE = DEFAULT_ROUTE | TREE_ROUTE

DEPENDENCIES = Optional[Sequence[params.Depends]]


class CRUDRouter(Generic[SERVICE], APIRouter):
    service: SERVICE
    max_items_get_many_routes: Optional[int]
    max_items_delete_many_routes: Optional[int]
    codes: Type[BaseCodes | DefaultCodes]

    def __init__(
            self,
            service: SERVICE,
            *,
            codes: Type[BaseCodes] = DefaultCodes,
            max_items_many_route: Optional[int] = None,
            max_items_get_many_route: Optional[int] = None,
            max_items_delete_many_route: Optional[int] = None,
            prefix: str = None,
            tags: Optional[list[str | Enum]] = None,
            auto_routes_only_dependencies: DEPENDENCIES = None,
            routes_kwargs: dict[ROUTE, bool | dict[str, Any]] = None,
            add_tree_routes: bool = False,
            **kwargs,
    ) -> None:
        self.service = service
        prefix = prefix.strip('/') if prefix else self.service.model.__name__.lower() + 's'
        tags = tags or [prefix]
        prefix = '/' + prefix
        super().__init__(prefix=prefix, tags=tags, **kwargs)

        self.codes = codes
        self.max_items_get_many_routes = max_items_get_many_route or max_items_many_route
        self.max_items_delete_many_routes = max_items_delete_many_route or max_items_many_route

        auto_routes_only_dependencies = auto_routes_only_dependencies or []
        routes_kwargs = routes_kwargs or {}

        routes_names = self.default_routes_names()
        if add_tree_routes:
            routes_names = *routes_names, self.tree_route_names()

        for route_name in routes_names:
            route_data = routes_kwargs.get(route_name, True)
            if route_data is False:
                continue
            self._register_route(route_name, route_data, auto_routes_only_dependencies)

    def _get_all_route(self) -> Callable[..., Any]:
        get_all = self.service.get_all
        list_item_schema = self.get_list_item_schema()

        async def route(
                response: Response,
                pagination: PAGINATION = pagination_factory(),
                sort: CommaSeparatedOf(str, wrapper=snake_case, in_query=True) = Query(None)
                # TODO: filters
        ):
            skip, limit = pagination
            result, total = await get_all(skip, limit, sort)
            response.headers.append('X-Total-Count', str(total))
            return [list_item_schema.from_orm(r) for r in result]

        return route

    def _get_many_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        max_items = self.max_items_get_many_routes
        get_many = self.service.get_many
        read_schema = self.get_read_schema()

        async def route(
                item_ids: CommaSeparatedOf(pk_field_type, max_items=max_items, in_query=True) = Query(..., alias='ids')
        ):
            results = await get_many(item_ids)
            return [read_schema.from_orm(r) for r in results]

        return route

    def _get_one_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        get_one = self.service.get_one
        read_schema = self.get_read_schema()

        async def route(item_id: pk_field_type = Path(...)):
            try:
                item = await get_one(item_id)
            except ItemNotFound:
                raise self.not_found_error()
            return read_schema.from_orm(item)

        return route

    def _create_route(self) -> Callable[..., Any]:
        create_schema = self.get_create_schema()
        read_schema = self.get_read_schema()
        create = self.service.create

        async def route(data: create_schema = Body(...)):
            try:
                return read_schema.from_orm(await create(data))
            except NotUnique as e:
                raise self.not_unique_error(e.fields)

        return route

    def _edit_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        read_schema = self.get_read_schema()
        edit_schema = self.get_edit_schema()
        edit = self.service.edit

        async def route(item_id: pk_field_type = Path(...), data: edit_schema = Body(...)):
            try:
                item = await edit(item_id, data)
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
                item_ids: CommaSeparatedOf(pk_field_type, max_items=max_items, in_query=True) = Query(..., alias='ids')
        ):
            deleted_items_count = await delete_many(item_ids)
            return self.ok_response(count=deleted_items_count)

        return route

    def _delete_one_route(self) -> Callable[..., Any]:
        pk_field_type = self.service.pk_field_type
        delete_one = self.service.delete_one

        async def route(item_id: pk_field_type = Path(...)):
            try:
                await delete_one(item_id)
            except ItemNotFound:
                raise self.not_found_error()
            return self.ok_response(item=item_id)

        return route

    def _ok_response_instance(self) -> BaseCodes:
        return self.codes.OK

    def ok_response(self, **kwargs) -> dict[str, Any]:
        if kwargs:
            return self._ok_response_instance().resp_detail(**kwargs)
        return self._ok_response_instance().resp

    def _not_found_error_instance(self) -> BaseCodes:
        return self.codes.not_found

    def not_found_error(self) -> BgHTTPException:
        return self._not_found_error_instance().err()

    def not_unique_error_instance(self) -> BaseCodes:
        return self.codes.not_unique_err

    def not_unique_error(self, fields: list[str]) -> BgHTTPException:
        return self.not_unique_error_instance().format_err(', '.join(fields), {'fields': fields})

    @staticmethod
    def default_routes_names() -> tuple[DEFAULT_ROUTE, ...]:
        return 'get_all', 'get_many', 'get_one', 'create', 'edit', 'delete_many', 'delete_one'

    @staticmethod
    def tree_route_names() -> tuple[TREE_ROUTE, ...]:
        return 'get_tree_node',

    @classmethod
    def all_route_names(cls) -> tuple[ROUTE, ...]:
        return *cls.default_routes_names(), *cls.tree_route_names()

    def _register_route(
            self,
            route_name: ROUTE,
            route_kwargs: bool | dict[str, Any],
            dependencies: Optional[Sequence[params.Depends]],
    ) -> None:
        responses = {}
        response_model = None
        status = 200
        match route_name:
            case 'get_all':
                path = '/all'
                method = ["GET"]
                response_model = list[self.get_list_item_schema()]
            case 'get_many':
                path = '/many'
                method = ["GET"]
                response_model = list[self.get_read_schema()]
            case 'get_one':
                path = '/one/{item_id}'
                method = ["GET"]
                response_model = self.get_read_schema()
                responses = self.codes.responses(self._not_found_error_instance())
            case 'get_tree_node':
                path = '/tree/{node_id}'
                method = ["GET"]
                response_model = self.get_list_item_schema()
            case 'create':
                path = ''
                method = ["POST"]
                response_model = self.get_read_schema()
                responses = self.codes.responses(
                    (self.not_unique_error_instance(), {'fields': ['поле1', 'поле2']})
                )
                status = 201
            case 'edit':
                path = '/{item_id}'
                method = ["PATCH"]
                response_model = self.get_read_schema()
                responses = self.codes.responses(
                    self._not_found_error_instance(),
                    (self.not_unique_error_instance(), {'fields': ['поле1', 'поле2']})
                )
            case 'delete_all':
                path = ''
                method = ["DELETE"]
                # don`t need response model, responses has one with status 200
                responses = self.codes.responses((self._ok_response_instance(), {'count': 10000}), )
            case 'delete_many':
                path = '/many'
                method = ["DELETE"]
                # don`t need response model, responses has one with status 200
                responses = self.codes.responses((self._ok_response_instance(), {'count': 30}), )
            case 'delete_one':
                path = '/{item_id}'
                method = ["DELETE"]
                # don`t need response model, responses has one with status 200
                responses = self.codes.responses((self._ok_response_instance(), {'item': 77}), )
            case _:
                raise Exception(f'Unknown name of route: {route_name}.\n'
                                f'Available are {", ".join(self.default_routes_names())}')
        summary = f"{route_name.title().replace('_', ' ')} {self.service.model.__name__}"

        route_kwargs = get_route_kwargs(route_kwargs, dependencies, responses)

        self.add_api_route(
            path=path,
            endpoint=getattr(self, f'_{route_name}_route')(),
            methods=method,
            response_model=response_model,
            summary=summary,
            status_code=status,
            **route_kwargs,
        )

    def get_read_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.service.get_read_schema(generate_if_not_exist=generate_if_not_exist)

    def get_list_item_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.service.get_list_item_schema(generate_if_not_exist=generate_if_not_exist)

    def get_create_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.service.get_create_schema(generate_if_not_exist=generate_if_not_exist)

    def get_edit_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.service.get_edit_schema(generate_if_not_exist=generate_if_not_exist)


def get_route_kwargs(
        route_data: bool | dict[str, Any],
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

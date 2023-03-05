from typing import Type, Any, TypeVar, Generic, Optional, Protocol, Callable, Sequence
from uuid import UUID

from fastapi import BackgroundTasks, Request

from ex_fastapi.pydantic import CamelModel
from ex_fastapi.auth.dependencies import user_with_perms
from .filters import BaseFilter

PK = TypeVar('PK', int, UUID)
DB_MODEL = TypeVar('DB_MODEL')


class Handler(Protocol):
    async def __call__(
            self,
            data,
            should_exclude: set[str],
            defaults: dict[str, Any] = None,
    ) -> DB_MODEL: ...


class QsRelatedFunc(Protocol):
    def __call__(self, path: str, method: str) -> set[str]: ...


class QsAnnotateFunc(Protocol):
    def __call__(self, path: str, method: str) -> dict[str, Any]: ...


class QsDefaultFiltersFunc(Protocol):
    def __call__(self, path: str, method: str) -> dict[str, Any]: ...


class BaseCRUDService(Generic[PK, DB_MODEL]):
    model: Type[DB_MODEL]

    read_schema: Type[CamelModel]
    list_item_schema: Type[CamelModel]
    create_schema: Optional[Type[CamelModel]]
    edit_schema: Optional[Type[CamelModel]]

    pk_field_type: Type[PK]
    pk_attr: str
    node_key: str

    queryset_select_related: QsRelatedFunc
    queryset_prefetch_related: QsRelatedFunc
    queryset_annotate_fields: QsAnnotateFunc
    queryset_default_filters: QsDefaultFiltersFunc

    create_handlers: dict[Type[DB_MODEL], Handler]
    edit_handlers: dict[Type[DB_MODEL], Handler]

    def __init__(
            self,
            db_model: Type[DB_MODEL],
            *,
            read_schema: Type[CamelModel] = None,
            read_list_item_schema: Type[CamelModel] = None,
            create_schema: Type[CamelModel] = None,
            edit_schema: Type[CamelModel] = None,
            queryset_select_related: QsRelatedFunc | set[str] = None,
            queryset_prefetch_related: QsRelatedFunc | set[str] = None,
            queryset_annotate_fields: QsAnnotateFunc | dict[str, Any] = None,
            queryset_default_filters: QsDefaultFiltersFunc | dict[str, Any] = None,
            node_key: str = 'parent_id',
            create_handlers: dict[Type[DB_MODEL], Handler] = None,
            edit_handlers: dict[Type[DB_MODEL], Handler] = None,
    ) -> None:
        ...

    # Смотри в tortoise-orm сервисе, используется lru_cache
    def _get_queryset(
            self,
            path: str,
            method: str,
            select_related: str,
            prefetch_related: str,
    ) -> Any:
        raise NotImplementedError()

    def get_queryset(
            self,
            request: Request,
            select_related: Sequence[str],
            prefetch_related: Sequence[str],
    ):
        raise NotImplementedError()

    def get_read_schema(self) -> Type[CamelModel]:
        return self.read_schema

    def get_list_item_schema(self) -> Type[CamelModel]:
        return self.list_item_schema or self.get_read_schema()

    def get_create_schema(self) -> Optional[Type[CamelModel]]:
        return self.create_schema

    def get_edit_schema(self) -> Optional[Type[CamelModel]]:
        return self.edit_schema

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: set[str],
            filters: list[BaseFilter],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> tuple[list[DB_MODEL], int]:
        raise NotImplementedError()

    async def get_many(
            self,
            item_ids: list[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> list[DB_MODEL]:
        raise NotImplementedError()

    async def get_one(
            self,
            item_id: PK,
            *,
            field_name: str = 'pk',
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> DB_MODEL:
        raise NotImplementedError()

    async def get_tree_node(
            self,
            node_id: Optional[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> list[DB_MODEL]:
        raise NotImplementedError()

    async def create(
            self,
            data: CamelModel,
            *,
            exclude: set[str] = None,
            model: Type[DB_MODEL] = None,
            background_tasks: BackgroundTasks = None,
            defaults: dict[str, Any] = None,
            request: Request = None,
            inside_transaction: bool = False,
    ) -> DB_MODEL:
        raise NotImplementedError()

    async def edit(
            self,
            item_id_or_instance: PK | DB_MODEL,
            data: CamelModel,
            *,
            exclude: set[str] = None,
            background_tasks: BackgroundTasks = None,
            defaults: dict[str, Any] = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
            inside_transaction: bool = False,
    ) -> DB_MODEL:
        raise NotImplementedError()

    async def delete_many(
            self,
            item_ids: list[PK],
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> int:
        raise NotImplementedError()

    async def delete_one(
            self,
            item_id: PK,
            *,
            background_tasks: BackgroundTasks = None,
            request: Request = None,
            select_related: Sequence[str] = (),
            prefetch_related: Sequence[str] = (),
    ) -> None:
        raise NotImplementedError()

    async def save_m2m(self, instance: DB_MODEL, data: CamelModel, m2m_fields: set[str], clear=True) -> None:
        raise NotImplementedError()

    def has_permissions(self, name: str) -> Callable[[...], bool]:
        return user_with_perms((self.model, name))

    def has_create_permissions(self) -> Callable[[...], bool]:
        return self.has_permissions('create')

    def has_get_permissions(self) -> Callable[[...], bool]:
        return self.has_permissions('get')

    def has_edit_permissions(self) -> Callable[[...], bool]:
        return self.has_permissions('edit')

    def has_delete_permissions(self) -> Callable[[...], bool]:
        return self.has_permissions('delete')

    def get_default_sort_fields(self) -> set[str]:
        raise NotImplementedError

from collections.abc import Sequence
from typing import Type, Any, TypeVar, Generic, Optional, Protocol
from uuid import UUID

from fastapi import BackgroundTasks

from ex_fastapi.pydantic import CamelModel
from .filters import BaseFilter

PK = TypeVar('PK', int, UUID)
DB_MODEL = TypeVar('DB_MODEL')


class Handler(Protocol):
    async def __call__(
            self,
            data: CamelModel,
            should_exclude: set[str] = None,
            **kwargs
    ): ...


class BaseCRUDService(Generic[PK, DB_MODEL]):
    model: DB_MODEL

    read_schema: Type[CamelModel]
    list_item_schema: Type[CamelModel]
    create_schema: Optional[Type[CamelModel]]
    edit_schema: Optional[Type[CamelModel]]

    pk_field_type: Type[PK]
    node_key: str

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
            queryset_select_related: Sequence[str] = None,
            queryset_prefetch_related: Sequence[str] = None,
            queryset_default_filters: dict[str, Any] = None,
            node_key: str = 'parent_id',
            create_handlers: dict[Type[DB_MODEL], Handler] = None,
            edit_handlers: dict[Type[DB_MODEL], Handler] = None,
    ) -> None:
        ...

    async def get_queryset(self) -> Any:
        raise NotImplementedError()

    def get_read_schema(self, generate_if_not_exist: bool = True) -> Type[CamelModel]:
        return self.read_schema

    def get_list_item_schema(self, generate_if_not_exist: bool = True) -> Type[CamelModel]:
        return self.list_item_schema or self.get_read_schema(generate_if_not_exist=generate_if_not_exist)

    def get_create_schema(self, generate_if_not_exist: bool = True) -> Optional[Type[CamelModel]]:
        return self.create_schema

    def get_edit_schema(self, generate_if_not_exist: bool = True) -> Optional[Type[CamelModel]]:
        return self.edit_schema

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: list[str],
            filters: list[BaseFilter],
            background_tasks: BackgroundTasks,
    ) -> tuple[list[DB_MODEL], int]:
        raise NotImplementedError()

    async def get_many(self, item_ids: list[PK], background_tasks: BackgroundTasks, **kwargs) -> list[DB_MODEL]:
        raise NotImplementedError()

    async def get_one(self, item_id: PK, background_tasks: BackgroundTasks, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def get_tree_node(self, node_id: Optional[PK], background_tasks: BackgroundTasks, **kwargs) -> list[DB_MODEL]:
        raise NotImplementedError()

    async def create(self, data: CamelModel, background_tasks: BackgroundTasks, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def edit(self, item_id: PK, data: CamelModel, background_tasks: BackgroundTasks, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def delete_many(self, item_ids: list[PK], background_tasks: BackgroundTasks, **kwargs) -> int:
        raise NotImplementedError()

    async def delete_one(self, item_id: PK, background_tasks: BackgroundTasks, **kwargs) -> None:
        raise NotImplementedError()

    def has_create_permissions(self):
        raise NotImplementedError()

    def has_get_permissions(self):
        raise NotImplementedError()

    def has_edit_permissions(self):
        raise NotImplementedError()

    def has_delete_permissions(self):
        raise NotImplementedError()

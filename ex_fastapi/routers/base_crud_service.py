from typing import Type, Any, TypeVar, Generic, Optional
from uuid import UUID

from ex_fastapi.pydantic import CamelModel
from ex_fastapi.routers.crud_router import NotUnique

PK = TypeVar('PK', int, UUID)
DB_MODEL = TypeVar('DB_MODEL')
SCHEMA = CamelModel


class BaseCRUDService(Generic[PK, DB_MODEL]):
    model: DB_MODEL
    read_schema: Type[SCHEMA]
    list_item_schema: Type[SCHEMA]
    create_schema: Optional[Type[SCHEMA]]
    edit_schema: Optional[Type[SCHEMA]]
    pk_field_type: Type[PK]

    async def get_queryset(self) -> Any:
        raise NotImplementedError()

    def get_read_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.read_schema

    def get_list_item_schema(self, generate_if_not_exist: bool = True) -> Type[SCHEMA]:
        return self.list_item_schema or self.get_read_schema(generate_if_not_exist=generate_if_not_exist)

    def get_create_schema(self, generate_if_not_exist: bool = True) -> Optional[Type[SCHEMA]]:
        return self.create_schema

    def get_edit_schema(self, generate_if_not_exist: bool = True) -> Optional[Type[SCHEMA]]:
        return self.edit_schema

    async def get_all(
            self,
            skip: Optional[int], limit: Optional[int],
            sort: list[str],
            **kwargs
    ) -> tuple[list[DB_MODEL], int]:
        raise NotImplementedError()

    async def get_many(self, item_ids: list[PK], *args, **kwargs) -> list[DB_MODEL]:
        raise NotImplementedError()

    async def get_one(self, item_id: PK, *args, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def create(self, data: SCHEMA, *args, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def edit(self, item_id: PK, data: SCHEMA, *args, **kwargs) -> DB_MODEL:
        raise NotImplementedError()

    async def delete_many(self, item_ids: list[PK], *args, **kwargs) -> int:
        raise NotImplementedError()

    async def delete_one(self, item_id: PK, *args, **kwargs) -> None:
        raise NotImplementedError()

    async def check_unique(self, data: dict[str]) -> list[str]:
        raise NotImplementedError()

    async def raise_if_not_unique(self, data: dict[str]) -> None:
        if not_unique_fields := await self.check_unique(data):
            raise NotUnique(fields=not_unique_fields)

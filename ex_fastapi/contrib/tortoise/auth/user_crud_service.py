from typing import Type

from ex_fastapi import CamelModel
from ex_fastapi.auth.schemas import get_user_default_schema, USER_SCHEMA
from .repo import UserRepository
from .. import TortoiseCRUDService


def get_user_crud_service(
        user_repo_cls: Type[UserRepository] = None,
        schemas: dict[USER_SCHEMA, CamelModel] = None,
        **crud_kwargs
) -> TortoiseCRUDService:
    user_repo_cls = user_repo_cls or UserRepository
    schemas = schemas or {}

    def get_schema(schema_name: USER_SCHEMA):
        return schemas.get(schema_name) or get_user_default_schema(schema_name)

    user_read = get_schema("UserRead")
    user_edit = get_schema("UserEdit")
    user_create = get_schema("UserCreate")

    return TortoiseCRUDService(
        user_repo_cls.model,
        read_schema=user_read,
        edit_schema=user_edit,
        create_schema=user_create,
        create_handlers={user_repo_cls.model: user_repo_cls.create_user},
        queryset_prefetch_related=('permissions', 'groups__permissions'),
        **crud_kwargs
    )

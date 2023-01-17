from typing import Type

from fastapi import APIRouter

from ex_fastapi import CRUDRouter, CamelModel
from ex_fastapi.auth.roles.schemas import get_roles_default_schema, ROLE_SCHEMAS


def get_roles_router(
        prefix: str = '/roles',
        schemas: dict[ROLE_SCHEMAS, Type[CamelModel]] = None
) -> APIRouter:
    # TODO: избавиться от импортов
    from ex_fastapi.contrib.tortoise import TortoiseCRUDService
    from ex_fastapi.contrib.tortoise.models import ContentType, Permission, PermissionGroup
    schemas = schemas or {}

    def get_schema(schema_name: ROLE_SCHEMAS) -> Type[CamelModel]:
        return schemas.get(schema_name) or get_roles_default_schema(schema_name)

    router = APIRouter(prefix=prefix)

    content_types_crud_service = TortoiseCRUDService(
        ContentType,
        read_schema=get_schema('ContentTypeRead')
    )
    router.include_router(CRUDRouter(
        service=content_types_crud_service,
        read_only=True,
    ))

    permissions_crud_service = TortoiseCRUDService(
        Permission,
        read_schema=get_schema('PermissionRead'),
        queryset_select_related=('content_type',)
    )
    router.include_router(CRUDRouter(
        service=permissions_crud_service,
        read_only=True,
    ))

    permission_groups_crud_service = TortoiseCRUDService(
        PermissionGroup,
        read_schema=get_schema('PermissionGroupRead'),
        edit_schema=get_schema('PermissionGroupEdit'),
        create_schema=get_schema('PermissionGroupCreate'),
        queryset_prefetch_related=('permissions__content_type',)
    )
    router.include_router(CRUDRouter(
        service=permission_groups_crud_service,
    ))

    return router

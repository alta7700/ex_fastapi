from fastapi import APIRouter

from ex_fastapi import CRUDRouter
from ex_fastapi.global_objects import get_crud_service
from ex_fastapi.pydantic.utils import get_schema
from ex_fastapi.models import Permission, PermissionGroup
from ex_fastapi.schemas import PermissionRead, PermissionGroupRead, PermissionGroupCreate, PermissionGroupEdit


CRUDService = get_crud_service()


def get_roles_router(prefix: str = '/roles', **kwargs) -> APIRouter:
    router = APIRouter(prefix=prefix, **kwargs)

    permissions_crud_service = CRUDService(
        Permission,
        read_schema=get_schema(PermissionRead),
    )
    router.include_router(CRUDRouter(
        service=permissions_crud_service,
        read_only=True,
    ))

    permission_groups_crud_service = CRUDService(
        PermissionGroup,
        read_schema=get_schema(PermissionGroupRead),
        edit_schema=get_schema(PermissionGroupEdit),
        create_schema=get_schema(PermissionGroupCreate),
    )
    router.include_router(CRUDRouter(
        service=permission_groups_crud_service,
    ))

    return router

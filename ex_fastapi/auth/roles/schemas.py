from typing import Optional, Type, Literal

from pydantic import Field

from ex_fastapi.pydantic import CamelModel, CamelModelORM, RelatedList

ROLE_SCHEMAS = Literal[
    "ContentTypeRead", "PermissionRead",
    "PermissionGroupRead", "PermissionGroupCreate", "PermissionGroupEdit",
]
roles_schemas: dict[ROLE_SCHEMAS, Type[CamelModel]] = {}


def set_roles_default_schemas() -> None:
    #TODO: избавиться от импортов
    from ex_fastapi.contrib.tortoise import max_len_of
    from ex_fastapi.contrib.tortoise.models import PermissionGroup

    max_len_pg = max_len_of(PermissionGroup)

    class ContentTypeRead(CamelModelORM):
        id: int
        name: str

    class PermissionRead(CamelModelORM):
        id: int
        name: str
        content_type: ContentTypeRead

    class PermissionGroupRead(CamelModelORM):
        id: int
        name: str
        permissions: RelatedList[PermissionRead]

    class PermissionGroupCreate(CamelModel):
        name: str = Field(max_length=max_len_pg('name'))
        permissions: list[int]

    class PermissionGroupEdit(CamelModel):
        name: Optional[str] = Field(max_length=max_len_pg('name'))
        permissions: Optional[list[int]]

    roles_schemas.update({
        "ContentTypeRead": ContentTypeRead,
        "PermissionRead": PermissionRead,
        "PermissionGroupRead": PermissionGroupRead,
        "PermissionGroupCreate": PermissionGroupCreate,
        "PermissionGroupEdit": PermissionGroupEdit,
    })


def get_roles_default_schema(schema_name: ROLE_SCHEMAS) -> Type[CamelModel]:
    if not roles_schemas:
        set_roles_default_schemas()
    return roles_schemas[schema_name]

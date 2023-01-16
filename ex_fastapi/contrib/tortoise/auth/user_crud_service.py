from typing import Type

from ex_fastapi import CamelModel
from ex_fastapi.auth.schemas import PasswordsPair, get_user_default_schema
from .repo import UserRepository
from .. import TortoiseCRUDService


def get_user_crud_service(
        user_repo_cls: Type[UserRepository] = None,
        user_read: Type[CamelModel] = None,
        user_edit: Type[CamelModel] = None,
        user_create: Type[CamelModel] = None,
        **crud_kwargs
) -> TortoiseCRUDService:
    user_repo_cls = user_repo_cls or UserRepository
    user_read = user_read or get_user_default_schema("UserRead")
    user_edit = user_edit or get_user_default_schema("UserEdit")
    user_create = user_create or get_user_default_schema("UserCreate")

    class UserCRUDService(TortoiseCRUDService):
        async def create(
                self,
                data: PasswordsPair,
                *,
                exclude: set[str] = None,
                check_unique: bool = True,
                **kwargs,
        ):
            if check_unique:
                await self.raise_if_not_unique(data.dict(exclude=exclude))
            return await user_repo_cls.create_user(data)

    return UserCRUDService(
        user_repo_cls.model,
        read_schema=user_read,
        edit_schema=user_edit,
        create_schema=user_create,
        **crud_kwargs
    )

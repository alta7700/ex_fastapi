from typing import Type

from fastapi import Body, Depends

from ex_fastapi import CamelModel
from ex_fastapi.auth import AuthErrors, AuthConsumer
from ex_fastapi.auth.schemas import BaseAuthSchema, _Token, get_user_default_schema
from ex_fastapi.contrib.tortoise.auth.repo import UserRepository


def get_sign_in_user(auth_schema: Type[BaseAuthSchema], user_repo_cls: Type[UserRepository]):
    async def wrapper(auth_data: auth_schema = Body()) -> UserRepository:

        field, value = auth_data.get_auth_field_and_value()
        user = await user_repo_cls.get_user_by(field, value).prefetch_related('groups', 'permissions')
        if user is None:
            raise AuthErrors.not_authenticated.err()
        user_repo = user_repo_cls(user)
        if not user_repo.verify_password(password=auth_data.password):
            raise AuthErrors.not_authenticated.err()
        return user_repo

    return wrapper


def auth_checker(
        public_key: str,
        token_user: Type[CamelModel] = None,
        user_repo_cls: Type[UserRepository] = None,
        cookie: bool = False,
        header: bool = False,
):
    auth_consumer = AuthConsumer(
        token_user=token_user or get_user_default_schema("TokenUser"),
        public_key=public_key
    )
    get_user_auth = auth_consumer.get_user_auth(cookie=cookie, header=header)
    user_repo_cls = user_repo_cls or UserRepository

    def get_user_with_perms(
            *permissions,
            select_related: tuple[str, ...] = (),
            prefetch_related: tuple[str, ...] = (),
    ):

        async def wrapper(token: _Token = Depends(get_user_auth)):
            query = user_repo_cls.model.all() \
                .select_related(*select_related) \
                .prefetch_related('groups__permissions', 'permissions', *(prefetch_related or ()))
            user = await query.get_or_none(id=token.user.id)
            if user is None or user.password_change_dt.timestamp() > token.iat or not user.is_active:
                raise AuthErrors.not_authenticated.err()
            user_repo = user_repo_cls(user)
            await user_repo.has_permissions(permissions)
            if not (user.is_superuser or await user_repo.has_permissions(permissions)):
                raise AuthErrors.permission_denied.err()
            return user_repo

        return wrapper

    return get_user_with_perms

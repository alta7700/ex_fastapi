from typing import Type, Literal, TYPE_CHECKING

from fastapi import Body, Depends

from ex_fastapi.global_objects import get_auth_errors, get_user_repository, get_auth_consumer
from ex_fastapi.schemas import Token, AuthSchema
from ex_fastapi.models import BaseModel
from ex_fastapi.pydantic import get_schema
from ex_fastapi.settings import get_settings

if TYPE_CHECKING:
    from ex_fastapi.auth.consumer import AuthConsumer


UserRepository = get_user_repository()
AuthErrors = get_auth_errors()


async def get_sign_in_user(auth_data: get_schema(AuthSchema) = Body()) -> UserRepository:

    field, value = auth_data.get_auth_field_and_value()
    user = await UserRepository.get_user_by(field, value).prefetch_related('groups', 'permissions')
    if user is None:
        raise AuthErrors.not_authenticated.err()
    user_repo = UserRepository(user)
    if not user_repo.verify_password(password=auth_data.password):
        raise AuthErrors.not_authenticated.err()
    return user_repo


def auth_checker(
        cookie: bool = False,
        header: bool = False,
        auth_consumer: "AuthConsumer" = None
):
    auth_consumer = auth_consumer or get_auth_consumer()
    get_user_auth = auth_consumer.get_user_auth(cookie=cookie, header=header)

    def get_user_with_perms(
            *permissions: tuple[Type[BaseModel], Literal['get', 'create', 'edit', 'delete']],
            select_related: tuple[str, ...] = (),
            prefetch_related: tuple[str, ...] = (),
    ):

        async def wrapper(token: Token = Depends(get_user_auth)):
            query = UserRepository.model.all() \
                .select_related(*select_related) \
                .prefetch_related('groups__permissions', 'permissions', *(prefetch_related or ()))
            user = await query.get_or_none(id=token.user.id)
            if user is None or user.password_change_dt.timestamp() > token.iat or not user.is_active:
                raise AuthErrors.not_authenticated.err()
            user_repo = UserRepository(user)
            if not (user.is_superuser or user_repo.has_permissions(permissions)):
                raise AuthErrors.permission_denied.err()
            return user_repo

        return wrapper

    return get_user_with_perms


auth_checker_params = get_settings('AUTH_CHECKER', default={
    'cookie': True,
    'header': False,
})
user_with_perms = auth_checker(**auth_checker_params)

from typing import Type, Literal, TYPE_CHECKING, Sequence

from fastapi import Body, Depends, Request

from ex_fastapi.global_objects import get_auth_errors, get_user_repository, get_auth_consumer, get_user_service
from ex_fastapi.routers.exceptions import ItemNotFound
from ex_fastapi.pydantic.utils import get_schema
from ex_fastapi.schemas import AuthSchema
from ex_fastapi.models import BaseModel
from .config import Token

if TYPE_CHECKING:
    from .consumer import AuthConsumer


UserRepository = get_user_repository()
AuthErrors = get_auth_errors()


def get_sign_in_user(
        select_related: Sequence[str] = (),
        prefetch_related: Sequence[str] = (),
):
    async def wrapper(
            request: Request,
            auth_data: get_schema(AuthSchema) = Body()
    ) -> UserRepository:

        field, value = auth_data.get_auth_field_and_value()
        try:
            user = await get_user_service().get_one(
                value,
                field_name=field,
                request=request,
                select_related=select_related,
                prefetch_related=prefetch_related,
            )
        except ItemNotFound:
            raise AuthErrors.not_authenticated.err()
        user_repo = UserRepository(user)
        if not user_repo.verify_password(password=auth_data.password):
            raise AuthErrors.not_authenticated.err()
        return user_repo

    return wrapper


async def get_user_by_token(
        token: "Token",
        request: Request,
        select_related: tuple[str, ...],
        prefetch_related: tuple[str, ...],
) -> UserRepository:
    try:
        user = await get_user_service().get_one(
            token.user.id,
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related
        )
    except ItemNotFound:
        raise AuthErrors.not_authenticated.err()
    user_repo = UserRepository(user)
    if not user_repo.can_login() or user_repo.token_expired(token):
        raise AuthErrors.not_authenticated.err()
    return user_repo


def get_user_by_refresh_token(
        auth_consumer: "AuthConsumer" = None,
        select_related: tuple[str, ...] = (),
        prefetch_related: tuple[str, ...] = (),
):
    auth_consumer = auth_consumer or get_auth_consumer()

    async def wrapper(
            request: Request,
            _token: str = Body(..., alias='refresh_token')
    ):
        token = auth_consumer.get_refresh_token(_token)
        return await get_user_by_token(
            token,
            request=request,
            select_related=select_related,
            prefetch_related=prefetch_related
        )

    return wrapper


def auth_checker(auth_consumer: "AuthConsumer" = None):
    def get_user_with_perms(
            *permissions: tuple[Type[BaseModel], Literal['get', 'create', 'edit', 'delete']],
            select_related: tuple[str, ...] = (),
            prefetch_related: tuple[str, ...] = (),
    ):
        get_user_auth = (auth_consumer or get_auth_consumer()).get_user_auth()

        async def wrapper(
                request: Request,
                token: "Token" = Depends(get_user_auth)
        ):
            user_repo = await get_user_by_token(
                token,
                request=request,
                select_related=select_related,
                prefetch_related=prefetch_related
            )
            if not (user_repo.is_superuser or user_repo.has_permissions(permissions)):
                raise AuthErrors.permission_denied.err()
            return user_repo

        return wrapper

    return get_user_with_perms


user_with_perms = auth_checker()

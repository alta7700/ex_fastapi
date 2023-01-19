from collections.abc import Callable
from typing import Type

from fastapi import APIRouter, Response, Depends

from ex_fastapi import CamelModel, BaseCodes
from ex_fastapi.auth import AuthErrors, AuthProvider
from ex_fastapi.auth.config import TokenTypes
from ex_fastapi.auth.schemas import get_user_default_schema, USER_SCHEMA


class DefaultCodes(BaseCodes):
    OK = 200, 'ОК'


def create_auth_router(
        private_key: str,
        access_token_lifetime: int = None,
        refresh_token_lifetime: int = None,
        prefix: str = '/auth',
        schemas: USER_SCHEMA = None,
        user_repo_cls=None,
) -> APIRouter:
    # TODO: избавиться от импортов
    from ex_fastapi.contrib.tortoise.auth.dependencies import get_sign_in_user, user_with_perms
    from ex_fastapi.contrib.tortoise.auth.repo import UserRepository

    schemas = schemas or {}

    def get_schema(schema_name: USER_SCHEMA) -> Type[CamelModel]:
        return schemas.get(schema_name) or get_user_default_schema(schema_name)

    user_me_read = get_schema("UserMeRead")
    auth_schema = get_schema("AuthSchema")
    token_user = get_schema("TokenUser")

    user_repo_cls: Type[UserRepository] = user_repo_cls or UserRepository

    token_lifetime = {}
    if access_token_lifetime:
        token_lifetime[TokenTypes.access] = access_token_lifetime
    if refresh_token_lifetime:
        token_lifetime[TokenTypes.refresh] = refresh_token_lifetime

    auth_provider = AuthProvider(
        token_user=token_user,
        user_me_read=user_me_read,
        private_key=private_key,
        lifetime=token_lifetime
    )

    router = APIRouter(prefix=prefix, tags=[prefix.strip('/')])

    @router.post('/login', response_model=user_me_read, responses=AuthErrors.responses(
        AuthErrors.not_authenticated
    ))
    async def login(
            response: Response,
            user_repo: user_repo_cls = Depends(get_sign_in_user(auth_schema, user_repo_cls)),
    ):
        if not await user_repo.can_login():
            raise AuthErrors.not_authenticated.err()
        auth_provider.set_auth_cookie(response, user_repo.user)
        return user_me_read.from_orm(user_repo.user)

    @router.get('/logout', responses=DefaultCodes.responses(DefaultCodes.OK))
    async def logout(response: Response):
        auth_provider.delete_auth_cookie(response)
        return DefaultCodes.OK.resp

    @router.get('/check', response_model=user_me_read, responses=AuthErrors.responses(*AuthErrors.all_errors()))
    async def get_me(
            response: Response,
            user_repo: UserRepository = Depends(user_with_perms())
    ):
        if not await user_repo.can_login():
            raise AuthErrors.not_authenticated.err()
        auth_provider.set_auth_cookie(response, user_repo.user)
        return user_me_read.from_orm(user_repo.user)

    return router

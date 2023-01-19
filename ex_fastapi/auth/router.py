from typing import TYPE_CHECKING

from fastapi import APIRouter, Response, Depends

from ex_fastapi.global_objects import \
    get_default_codes, get_auth_errors, \
    get_user_repository, get_crud_service,\
    get_auth_provider, get_auth_dependencies
from ex_fastapi.pydantic import get_schema
from ex_fastapi.schemas import UserMeRead, TokenUser, UserRead, UserEdit, UserCreate
from ex_fastapi.routers import CRUDRouter

if TYPE_CHECKING:
    from ex_fastapi.auth import AuthProvider


DefaultCodes = get_default_codes()
UserRepository = get_user_repository()
UserMeRead = get_schema(UserMeRead)
TokenUser = get_schema(TokenUser)
AuthErrors = get_auth_errors()
dependencies = get_auth_dependencies()


def create_auth_router(
        prefix: str = '/auth',
        auth_provider: "AuthProvider" = None,
        include_users: bool = True,
        **kwargs
) -> APIRouter:

    auth_provider = auth_provider or get_auth_provider()
    auth_tags = [prefix.strip('/')]
    router = APIRouter(prefix=prefix, **kwargs)

    @router.post('/login', tags=auth_tags, response_model=UserMeRead, responses=AuthErrors.responses(
        AuthErrors.not_authenticated
    ))
    async def login(
            response: Response,
            user_repo: UserRepository = Depends(dependencies.get_sign_in_user),
    ):
        if not await user_repo.can_login():
            raise AuthErrors.not_authenticated.err()
        auth_provider.set_auth_cookie(response, user_repo.user)
        return UserMeRead.from_orm(user_repo.user)

    @router.get('/logout', tags=auth_tags, responses=DefaultCodes.responses(DefaultCodes.OK))
    async def logout(response: Response):
        auth_provider.delete_auth_cookie(response)
        return DefaultCodes.OK.resp

    @router.get('/check', tags=auth_tags, response_model=UserMeRead,
                responses=AuthErrors.responses(*AuthErrors.all_errors()))
    async def get_me(
            response: Response,
            user_repo: UserRepository = Depends(dependencies.user_with_perms())
    ):
        if not await user_repo.can_login():
            raise AuthErrors.not_authenticated.err()
        auth_provider.set_auth_cookie(response, user_repo.user)
        return UserMeRead.from_orm(user_repo.user)

    if include_users:

        user_crud_service = get_crud_service()(
            UserRepository.model,
            read_schema=get_schema(UserRead),
            edit_schema=get_schema(UserEdit),
            create_schema=get_schema(UserCreate),
            create_handlers={UserRepository.model: UserRepository.create_user},
            queryset_prefetch_related=('permissions', 'groups__permissions'),
        )

        router.include_router(CRUDRouter(
            service=user_crud_service,
            max_items_many_route=100,
        ))

    return router

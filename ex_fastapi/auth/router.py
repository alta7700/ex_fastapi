from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Response, Depends, BackgroundTasks, Body, Query

from ex_fastapi.global_objects import \
    get_default_codes, get_auth_errors, \
    get_user_repository, get_crud_service,\
    get_auth_provider, get_auth_dependencies
from ex_fastapi.pydantic import get_schema
from ex_fastapi.schemas import UserMeRead, UserRead, UserEdit, UserCreate, UserRegistration
from ex_fastapi.routers import CRUDRouter
from ex_fastapi.routers.exceptions import NotUnique

if TYPE_CHECKING:
    from ex_fastapi.auth.provider import AuthProvider


Codes = get_default_codes()
UserRepository = get_user_repository()
UserMeRead = get_schema(UserMeRead)
AuthErrors = get_auth_errors()
dependencies = get_auth_dependencies()


def create_auth_router(
        prefix: str = '/auth',
        auth_provider: "AuthProvider" = None,
        include_users: bool | dict[str, Any] = True,
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

    @router.get('/logout', tags=auth_tags, responses=Codes.responses(Codes.OK))
    async def logout(response: Response):
        auth_provider.delete_auth_cookie(response)
        return Codes.OK.resp

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
        if include_users is True:
            include_users = {}
        router.include_router(create_users_router(routes_kwargs=include_users))

    return router


def create_users_router(**kwargs) -> CRUDRouter:
    service = get_crud_service()(
        UserRepository.model,
        read_schema=get_schema(UserRead),
        create_schema=get_schema(UserCreate),
        edit_schema=get_schema(UserEdit),
        create_handlers={UserRepository.model: UserRepository.create_user},
        queryset_prefetch_related=('permissions', 'groups__permissions'),
    )

    router = CRUDRouter(service=service, **kwargs)

    @router.post('/registration', status_code=201, responses=Codes.responses(
        (Codes.activation_email, {'uuid': uuid4()}),
        (router.not_unique_error_instance(), {'fields': ['поле1', 'поле2']})
    ))
    async def registration(
            background_tasks: BackgroundTasks,
            data: get_schema(UserRegistration) = Body(...)
    ):
        try:
            user = await router.service.create(data, background_tasks=background_tasks)
        except NotUnique as e:
            raise router.not_unique_error(e.fields)
        user_repo = UserRepository(user)
        await user_repo.post_registration(background_tasks)
        return Codes.activation_email.resp_detail(uuid=user_repo.uuid)

    @router.get('/activation', response_model=UserMeRead, responses=Codes.responses(
        router.not_found_error_instance(),
        Codes.activation_email_resend,
        Codes.activation_email_code_incorrect,
        Codes.already_active,
    ))
    async def activate_account(
            background_tasks: BackgroundTasks,
            uuid: UUID = Query(...),
            code: str = Query(min_length=6, max_length=6)
    ):
        user = await UserRepository.get_user_by('uuid', uuid).select_related('temp_code')
        if not user:
            raise router.not_found_error()
        user_repo = UserRepository(user)
        if user_repo.is_user_active:
            raise Codes.already_active.err()
        temp_code_error = user_repo.check_temp_code_error(code)
        if temp_code_error:
            if temp_code_error == 'expired':
                user_repo.add_send_activation_email_task(background_tasks=background_tasks)
                raise Codes.activation_email_resend.err(background=background_tasks)
            if temp_code_error == 'incorrect':
                raise Codes.activation_email_code_incorrect.err()
        await user_repo.activate()
        return UserMeRead.from_orm(user_repo.user)
    return router

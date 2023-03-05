from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import APIRouter, Response, Depends, BackgroundTasks, Body, Query, Request

from ex_fastapi.global_objects import \
    get_default_codes, get_auth_errors, \
    get_user_repository, get_user_service, \
    get_auth_provider
from ex_fastapi.pydantic.utils import get_schema
from ex_fastapi.schemas import UserMeRead, UserMeEdit, UserRegistration
from ex_fastapi.routers import CRUDRouter
from ex_fastapi.routers.exceptions import MultipleFieldsError
from .dependencies import get_sign_in_user, user_with_perms, get_user_by_refresh_token
from .roles.router import get_roles_router

if TYPE_CHECKING:
    from .provider import AuthProvider


Codes = get_default_codes()
UserRepository = get_user_repository()
UserMeRead = get_schema(UserMeRead)
AuthErrors = get_auth_errors()


def create_auth_router(
        prefix: str = '/auth',
        auth_provider: "AuthProvider" = None,
        **kwargs
) -> APIRouter:

    auth_provider = auth_provider or get_auth_provider()
    router = APIRouter(prefix=prefix, **kwargs)

    @router.post(
        '/login', tags=kwargs.get('tags', [prefix.strip('/')]),
        response_model=auth_provider.authorize_response_model,
        responses=AuthErrors.responses(AuthErrors.not_authenticated),
    )
    async def login(
            response: Response,
            user_repo: UserRepository = Depends(get_sign_in_user()),
    ):
        if not user_repo.can_login():
            raise AuthErrors.not_authenticated.err()
        return auth_provider.authorize(response, user_repo.user)

    if auth_provider.auth_method == 'cookie':
        @router.get('/logout', tags=kwargs.get('tags', [prefix.strip('/')]), responses=Codes.responses(Codes.OK))
        async def logout(response: Response):
            auth_provider.delete_auth_cookie(response)
            return Codes.OK.resp

    if auth_provider.auth_method == 'header':
        @router.post(
            '/refresh', tags=kwargs.get('tags', [prefix.strip('/')]),
            response_model=auth_provider.authorize_response_model,
            responses=Codes.responses(*AuthErrors.all_errors())
        )
        async def token_refresh(
                response: Response,
                user_repo: "UserRepository" = Depends(get_user_by_refresh_token())
        ):
            return auth_provider.authorize(response, user_repo.user)

    return router


def create_users_router(
        auth_provider: "AuthProvider" = None,
        add_registration_route: bool = True,
        add_activate_account_route: bool = True,
        add_get_me_route: bool = True,
        add_edit_me_route: bool = True,
        complete_auto_routes: bool = True,
        **kwargs
) -> CRUDRouter:

    auth_provider = auth_provider or get_auth_provider()

    router = CRUDRouter(service=get_user_service(), complete_auto_routes=False, **kwargs)

    if add_registration_route:
        @router.post('/registration', status_code=201, responses=Codes.responses(
            (Codes.activation_email, {'uuid': uuid4()}),
            router.field_errors_response_example()
        ))
        async def registration(
                request: Request,
                background_tasks: BackgroundTasks,
                data: get_schema(UserRegistration) = Body(...)
        ):
            try:
                user = await router.service.create(
                    data,
                    background_tasks=background_tasks,
                    request=request
                )
            except MultipleFieldsError as e:
                raise router.field_errors(e)
            user_repo = UserRepository(user)
            await user_repo.post_registration(background_tasks)
            return Codes.activation_email.resp_detail(uuid=user_repo.uuid)

    if add_activate_account_route:
        @router.get('/activation', response_model=auth_provider.authorize_response_model, responses=Codes.responses(
            router.not_found_error_instance(),
            Codes.activation_email_resend,
            Codes.activation_email_code_incorrect,
            Codes.already_active,
        ))
        async def activate_account(
                request: Request,
                response: Response,
                background_tasks: BackgroundTasks,
                uuid: UUID = Query(...),
                code: str = Query(..., min_length=6, max_length=6)
        ):
            user = await router.service.get_one(
                uuid, field_name='uuid',
                background_tasks=background_tasks,
                request=request,
            )
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
            return auth_provider.authorize(response, user_repo.user)

    if add_get_me_route:
        @router.get('/me', response_model=auth_provider.authorize_response_model, responses=AuthErrors.responses(
            *AuthErrors.all_errors()
        ))
        async def get_me(
                response: Response,
                user_repo: UserRepository = Depends(user_with_perms())
        ):
            if not user_repo.can_login():
                raise AuthErrors.not_authenticated.err()
            return auth_provider.authorize(response, user_repo.user)

    if add_edit_me_route:
        @router.patch('/me', response_model=auth_provider.authorize_response_model, responses=AuthErrors.responses(
            *AuthErrors.all_errors(),
            router.field_errors_response_example()
        ))
        async def edit_me(
                response: Response,
                background_tasks: BackgroundTasks,
                user_repo: UserRepository = Depends(user_with_perms()),
                data: get_schema(UserMeEdit) = Body(...),
        ):
            try:
                user = await router.service.edit(user_repo.user, data, background_tasks=background_tasks)
            except MultipleFieldsError as e:
                raise router.field_errors(e)
            return auth_provider.authorize(response, user)

    if complete_auto_routes:
        router.complete_auto_routes()
    return router

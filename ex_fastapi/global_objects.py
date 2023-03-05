from importlib import import_module
from typing import Type, TYPE_CHECKING, Optional

from pydantic.utils import import_string

from ex_fastapi.settings import get_settings, get_settings_obj
from ex_fastapi.pydantic.utils import get_schema

if TYPE_CHECKING:
    from ex_fastapi.auth.base_repository import BaseUserRepository, UserInterface
    from ex_fastapi.auth.consumer import AuthConsumer
    from ex_fastapi.auth.provider import AuthProvider
    from ex_fastapi.routers import BaseCRUDService
    from ex_fastapi.code_responces import DefaultCodes, BaseCodes, AuthErrors


def get_default_codes() -> Type["BaseCodes"] | Type["DefaultCodes"]:
    codes_str = get_settings('DEFAULT_CODES', default='codes.Codes')
    try:
        return import_string(codes_str)
    except ImportError:
        from ex_fastapi.code_responces import DefaultCodes
        return DefaultCodes


def get_auth_errors() -> Type["BaseCodes"] | Type["AuthErrors"]:
    codes_str = get_settings('AUTH_ERRORS', default='codes.AuthErrors')
    try:
        return import_string(codes_str)
    except ImportError:
        from ex_fastapi.code_responces import AuthErrors
        return AuthErrors


def get_user_repository() -> Type["BaseUserRepository"]:
    db_name: str = get_settings("db_name")
    user_repo_str = get_settings(
        'USER_REPOSITORY',
        default=f'ex_fastapi.contrib.{db_name}.user_repository.UserRepository'
    )
    return import_string(user_repo_str)


def get_user_model_path() -> str:
    return get_settings('USER_MODEL', 'models.User')


def get_user_model() -> "UserInterface":
    return import_string(get_user_model_path())


def get_crud_service() -> Type["BaseCRUDService"]:
    db_name = get_settings('db_name')
    crud_service_str = get_settings(
        'MAIN_CRUD_SERVICE',
        default=f'ex_fastapi.contrib.{db_name}.crud_service.{db_name.title()}CRUDService'
    )
    return import_string(crud_service_str)


USER_SERVICE: Optional["BaseCRUDService[UserInterface]"] = None


def get_user_service() -> "BaseCRUDService[int, UserInterface]":
    global USER_SERVICE
    if USER_SERVICE is None:
        user_service_str = get_settings('USER_SERVICE', default=None)
        if user_service_str:
            USER_SERVICE = import_string(user_service_str)
        else:
            from ex_fastapi.auth.schemas import UserRead, UserCreate, UserEdit
            user_repository_cls = get_user_repository()
            USER_SERVICE = get_crud_service()(
                user_repository_cls.model,
                read_schema=get_schema(UserRead),
                create_schema=get_schema(UserCreate),
                edit_schema=get_schema(UserEdit),
                create_handlers={user_repository_cls.model: user_repository_cls.create_user},
            )
    return USER_SERVICE


AUTH_CONSUMER: Optional["AuthConsumer"] = None
AUTH_PROVIDER: Optional["AuthProvider"] = None


def get_auth_consumer() -> "AuthConsumer":
    global AUTH_CONSUMER
    if AUTH_CONSUMER is None:
        auth_consumer_str = get_settings('AUTH_CONSUMER', default=None)
        if auth_consumer_str:
            AUTH_CONSUMER = import_string(auth_consumer_str)
        else:
            from ex_fastapi.auth.consumer import AuthConsumer
            user_auth_strategy = get_settings('AUTH_STRATEGY', default={})
            AUTH_CONSUMER = AuthConsumer(
                public_key=get_settings_obj().RSA_PUBLIC,
                strategy=user_auth_strategy,
            )
    return AUTH_CONSUMER


def get_auth_provider() -> "AuthProvider":
    global AUTH_PROVIDER
    if AUTH_PROVIDER is None:
        auth_provider_str = get_settings('AUTH_PROVIDER', default=None)
        if auth_provider_str:
            AUTH_PROVIDER = import_string(auth_provider_str)
        else:
            from ex_fastapi.auth.provider import AuthProvider
            from ex_fastapi.auth.config import TokenTypes
            user_auth_strategy = get_settings('AUTH_STRATEGY', default={})
            settings_obj = get_settings_obj()
            AUTH_PROVIDER = AuthProvider(
                private_key=settings_obj.RSA_PRIVATE,
                strategy=user_auth_strategy,
                lifetime={
                    TokenTypes.access: settings_obj.access_token_lifetime,
                    TokenTypes.refresh: settings_obj.refresh_token_lifetime,
                }
            )
    return AUTH_PROVIDER


def get_auth_dependencies():
    return import_module(f'ex_fastapi.contrib.{get_settings("db_name")}.auth_dependencies')

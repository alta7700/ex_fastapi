from importlib import import_module
from typing import Type, TYPE_CHECKING, Optional

from pydantic.utils import import_string

from ex_fastapi.settings import get_settings, get_settings_obj

if TYPE_CHECKING:
    from ex_fastapi.auth.base_repository import BaseUserRepository
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


def get_user_model():
    return import_string(get_user_model_path())


def get_crud_service() -> Type["BaseCRUDService"]:
    db_name = get_settings('db_name')
    crud_service_str = get_settings(
        'MAIN_CRUD_SERVICE',
        default=f'ex_fastapi.contrib.{db_name}.crud_service.{db_name.title()}CRUDService'
    )
    return import_string(crud_service_str)


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
            AUTH_CONSUMER = AuthConsumer(public_key=get_settings_obj().RSA_PUBLIC)
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
            settings_obj = get_settings_obj()
            AUTH_PROVIDER = AuthProvider(
                private_key=settings_obj.RSA_PRIVATE,
                lifetime={
                    TokenTypes.access: settings_obj.access_token_lifetime,
                    TokenTypes.refresh: settings_obj.refresh_token_lifetime,
                }
            )
    return AUTH_PROVIDER


def get_auth_dependencies():
    return import_module(f'ex_fastapi.contrib.{get_settings("db_name")}.auth_dependencies')

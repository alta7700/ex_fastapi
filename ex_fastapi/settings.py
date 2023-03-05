import os
from importlib import import_module
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseSettings as PydanticBaseSettings, DirectoryPath, AnyHttpUrl


MODE = os.environ.get('MODE') or 'DEBUG'
DEBUG = MODE == 'DEBUG'
DEV = MODE == 'DEV'
PROD = MODE == 'PROD'


class Databases(Enum):
    tortoise = 'tortoise'


if DEBUG:
    class SettingsConfig(PydanticBaseSettings.Config):
        env_file = '.env'
else:
    SettingsConfig = PydanticBaseSettings.Config

try:
    from fastapi_mail import ConnectionConfig

    class MailingConfig(ConnectionConfig):
        TEMPLATE_FOLDER: DirectoryPath = Path(__file__).parent / 'templates'

        Config = SettingsConfig
except ImportError:
    MailingConfig, ConnectionConfig = None, None


class BaseSettings(PydanticBaseSettings):

    COOKIE_SECURE: bool = False
    RSA_PRIVATE: str
    RSA_PUBLIC: str
    ACCESS_TOKEN_LIFETIME: int = 5
    REFRESH_TOKEN_LIFETIME: int = 10
    SITE: AnyHttpUrl = 'http://localhost:8000'

    Config = SettingsConfig

    @property
    def access_token_lifetime(self) -> int:
        return int(timedelta(minutes=self.ACCESS_TOKEN_LIFETIME).total_seconds())

    @property
    def refresh_token_lifetime(self) -> int:
        return int(timedelta(days=self.REFRESH_TOKEN_LIFETIME).total_seconds())

    @property
    def cookie_secure(self) -> bool:
        return self.SITE.scheme == 'https'


def get_settings(var: str, default: Any = '__undefined__') -> Any:
    settings = import_module('settings')
    match var:
        case 'db_name':
            return getattr(settings, 'DB_PROVIDER', Databases.tortoise).value
        case _:
            if default == '__undefined__':
                return getattr(settings, var)
            return getattr(settings, var, default)


def get_settings_obj() -> BaseSettings:
    return get_settings('settings')

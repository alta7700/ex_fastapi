import os
from importlib import import_module
from datetime import timedelta
from enum import Enum
from typing import Optional, Any

from pydantic import BaseSettings as PydanticBaseSettings, PyObject


MODE = os.environ.get('MODE') or 'DEBUG'
DEBUG = MODE == 'DEBUG'
DEV = MODE == 'DEV'
PROD = MODE == 'PROD'


class Databases(Enum):
    default = 'tortoise'
    tortoise = 'tortoise'


if DEBUG:
    class SettingsConfig(PydanticBaseSettings.Config):
        env_file = '.env'
else:
    SettingsConfig = PydanticBaseSettings.Config


class BaseSettings(PydanticBaseSettings):

    COOKIE_SECURE: bool = False
    RSA_PRIVATE: str
    RSA_PUBLIC: str
    ACCESS_TOKEN_LIFETIME: int = 5
    REFRESH_TOKEN_LIFETIME: int = 10

    Config = SettingsConfig

    @property
    def access_token_lifetime(self) -> int:
        return int(timedelta(minutes=self.ACCESS_TOKEN_LIFETIME).total_seconds())

    @property
    def refresh_token_lifetime(self) -> int:
        return int(timedelta(days=self.REFRESH_TOKEN_LIFETIME).total_seconds())


def get_settings(var: str = 'settings', default: Any = '__undefined__') -> Any:
    settings = import_module('settings')
    match var:
        case 'db_name':
            return getattr(settings, 'DB_PROVIDER', Databases.default).value
        case _:
            if default == '__undefined__':
                return getattr(settings, var)
            return getattr(settings, var, default)


def get_settings_obj() -> BaseSettings:
    return get_settings()

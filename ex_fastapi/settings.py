import importlib
import os

from pydantic import BaseSettings as PydanticBaseSettings


MODE = os.environ.get('MODE') or 'DEBUG'
DEBUG = MODE == 'DEBUG'
DEV = MODE == 'DEV'
PROD = MODE == 'PROD'


if DEBUG:
    class BaseSettings(PydanticBaseSettings):
        class Config(PydanticBaseSettings.Config):
            env_file = '.env'
else:
    BaseSettings = PydanticBaseSettings


def get_settings():
    return importlib.import_module('settings')

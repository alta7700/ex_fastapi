from typing import TypeVar

from pydantic.utils import import_string
from ex_fastapi.global_objects import get_settings

_T = TypeVar('_T')


def get_schema(default: _T) -> _T:
    try:
        return import_string(f'schemas.{default.__name__}')
    except ImportError as e:
        if not get_settings('PROD'):
            print(e)
        return default

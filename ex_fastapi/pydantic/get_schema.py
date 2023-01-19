from typing import TypeVar

from pydantic.utils import import_string


_T = TypeVar('_T')


def get_schema(default: _T) -> _T:
    try:
        return import_string(f'schemas.{default.__name__}')
    except ImportError:
        return default

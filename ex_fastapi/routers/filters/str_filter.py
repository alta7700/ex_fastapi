from typing import TypedDict, Self, Any

from . import BaseFilter, BaseFilterValidator


class StrFilterOpts(TypedDict, total=False):
    min_length: int
    max_length: int


class StrFilterValidator(BaseFilterValidator[StrFilterOpts], str):
    min_length: int = None
    max_length: int = None

    @classmethod
    def validate(cls, v: str) -> Self:
        v_len = len(v)
        if cls.min_length is not None and v_len < cls.min_length:
            raise ValueError('Value is too short')
        if cls.max_length is not None and v_len > cls.max_length:
            raise ValueError('Value is too long')
        return cls(v)

    @classmethod
    def __schema__(cls) -> dict[str, Any]:
        return {
            'type': 'string',
            'example': 'Просто строка',
            'min_length': cls.min_length,
            'max_length': cls.max_length,
        }


class BaseStrFilter(BaseFilter[str, StrFilterOpts, StrFilterValidator]):
    base_validator = StrFilterValidator

    @classmethod
    def describe(cls):
        return 'Обычный строковый фильтр, вводи строку'

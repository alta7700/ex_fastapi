from typing import TypedDict, Self

from . import BaseFilter, BaseFilterValidator


class IntFilterOpts(TypedDict, total=False):
    min_value: int
    max_value: int


class IntFilterValidator(BaseFilterValidator[IntFilterOpts], int):
    min_value: int = None
    max_value: int = None

    @classmethod
    def validate(cls, v: str) -> Self:
        v = int(v)
        if cls.min_value is not None and v < cls.min_value:
            raise ValueError('Value is too short')
        if cls.max_value is not None and v > cls.max_value:
            raise ValueError('Value is too long')
        return cls(v)


class BaseIntFilter(BaseFilter[int, IntFilterOpts]):
    base_validator = IntFilterValidator

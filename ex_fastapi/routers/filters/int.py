from typing import TypedDict, Self, Any

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
            raise ValueError(f'The value is less than the minimum ({cls.min_value})')
        if cls.max_value is not None and v > cls.max_value:
            raise ValueError(f'The value is greater than the maximum ({cls.max_value})')
        return cls(v)

    @classmethod
    def __schema__(cls) -> dict[str, Any]:
        return {
            'type': 'number',
            'minimum': cls.min_value,
            'maximum': cls.max_value,
        }


class BaseIntFilter(BaseFilter[int, IntFilterOpts, IntFilterValidator]):
    base_validator = IntFilterValidator

    @classmethod
    def describe(cls):
        return 'Обычный числовой фильтр, вводи число'

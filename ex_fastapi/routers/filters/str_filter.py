from typing import TypedDict, Self

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


class BaseStrFilter(BaseFilter[str, StrFilterOpts]):
    base_validator = StrFilterValidator

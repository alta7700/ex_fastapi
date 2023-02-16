from typing import TypedDict, Self

from . import BaseFilter, BaseFilterValidator


BOOL_FALSE = {0, '0', 'off', 'f', 'false', 'n', 'no'}
BOOL_TRUE = {1, '1', 'on', 't', 'true', 'y', 'yes'}


class BoolFilterOpts(TypedDict, total=False):
    strict: bool


class BoolFilterValidator(BaseFilterValidator[BoolFilterOpts]):
    strict: bool = False

    # bool is not subclassable, so we return bool, not Self
    @classmethod
    def validate(cls, v: str) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, bytes):
            v = v.decode()
        if isinstance(v, str):
            v = v.lower()
        if cls.strict:
            if v == 'true':
                return True
            elif v == 'false':
                return False
            else:
                raise ValueError('Only true or false is allowed')
        if v in BOOL_TRUE:
            return True
        elif v in BOOL_FALSE:
            return False
        else:
            raise ValueError('Can`t translate value to boolean')


class BaseBoolFilter(BaseFilter[str, BoolFilterValidator]):
    base_validator = BoolFilterValidator

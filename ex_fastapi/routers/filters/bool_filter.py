from typing import TypedDict, Any

from . import BaseFilter, BaseFilterValidator


BOOL_FALSE = {0, '0', 'off', 'f', 'false', 'n', 'no'}
BOOL_TRUE = {1, '1', 'on', 't', 'true', 'y', 'yes'}


class BoolFilterOpts(TypedDict, total=False):
    pass


class BoolFilterValidator(BaseFilterValidator[BoolFilterOpts]):
    # bool is not subclassable, so we return bool, not Self
    @classmethod
    def validate(cls, v: str) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, bytes):
            v = v.decode()
        if isinstance(v, str):
            v = v.lower()
        if v in BOOL_TRUE:
            return True
        elif v in BOOL_FALSE:
            return False
        else:
            raise ValueError('Can`t translate value to boolean')

    @classmethod
    def __schema__(cls) -> dict[str, Any]:
        return {'type': 'boolean'}


class BaseBoolFilter(BaseFilter[str, BoolFilterOpts, BoolFilterValidator]):
    base_validator = BoolFilterValidator

    @classmethod
    def describe(cls):
        return "Булевый фильтр, принимает значения False - 0,off,f,false,n,no; True - 1,on,t,true,y,yes"

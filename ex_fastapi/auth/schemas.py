from typing import Generic, TypeVar, Any

from pydantic import root_validator

from ex_fastapi.pydantic import CamelModel
from ex_fastapi.pydantic.camel_model import CamelGeneric
from .config import TokenTypes

USER = TypeVar('USER', bound=CamelModel)


class _Token(CamelGeneric, Generic[USER]):
    type: TokenTypes
    user: USER
    iat: int  # timestamp


class _TokenIssue(CamelGeneric, Generic[USER]):
    type: TokenTypes
    user: USER
    iat: int  # timestamp
    exp: int  # timestamp

    @root_validator(pre=True)
    def calc_ext(cls, values: dict[str, Any]) -> dict[str, Any]:
        if 'exp' not in values:
            seconds = values['lifetime'][values['type']]
            values["exp"] = values["iat"] + seconds
        return values


class _TokenPair(CamelGeneric, Generic[USER]):
    access_token: str
    refresh_token: str
    user: USER

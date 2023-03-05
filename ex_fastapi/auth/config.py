from typing import TypedDict, Literal
from enum import Enum

from jwt import PyJWT

from ex_fastapi.pydantic import CamelModel
from ex_fastapi.pydantic.utils import get_schema
from .schemas import TokenUser


class TokenTypes(Enum):
    refresh = 'refresh'
    access = 'access'


class BaseJWTConfig:
    ALGORITHM = "RS256"
    jwt = PyJWT()


class AuthStrategy(TypedDict, total=False):
    method: Literal['cookie', 'header']
    schema: str


def auth_strategy_is_valid(values: AuthStrategy) -> bool:
    return values['method'] in ('cookie', 'header')


default_auth_strategy: AuthStrategy = {
    'method': 'cookie',
    'schema': 'bearer',
}


class Token(CamelModel):
    type: TokenTypes
    user: get_schema(TokenUser)
    iat: int  # timestamp

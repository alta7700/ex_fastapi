from enum import Enum

from jwt import PyJWT


class TokenTypes(Enum):
    refresh = 'refresh'
    access = 'access'


class BaseJWTConfig:
    ALGORITHM = "RS256"
    jwt = PyJWT()

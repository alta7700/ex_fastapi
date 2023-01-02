from typing import Any, Optional, Type

from fastapi import Cookie
from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError

from ex_fastapi import CamelModel
from .config import BaseJWTConfig, TokenTypes
from .auth_errors import AuthErrors
from .schemas import _Token


class JWTConsumer(BaseJWTConfig):
    PUBLIC_KEY: str

    def __init__(self, public_key: str):
        self.PUBLIC_KEY = public_key.strip("'").strip('"')

    def decode(self, token: str) -> dict[str, Any]:
        return self.jwt.decode(token, self.PUBLIC_KEY, [self.ALGORITHM])


class AuthConsumer:

    jwt: JWTConsumer

    def __init__(
            self,
            token_user: Type[CamelModel],
            public_key: str
    ):
        self.Token = _Token[token_user]
        self.jwt = JWTConsumer(public_key=public_key)

    def get_token_payload(self, token: str):
        try:
            payload = self.jwt.decode(token)
        except (InvalidSignatureError, DecodeError):
            raise AuthErrors.invalid_token.err()
        except ExpiredSignatureError:
            raise AuthErrors.expired_token.err()
        return self.Token(**payload)

    def parse_token(self, token: str) -> _Token:
        payload = self.get_token_payload(token)
        if payload.type != TokenTypes.access:
            raise AuthErrors.not_authenticated.err()
        return payload

    def get_auth(self, schema_required: str, token: str) -> _Token:
        schema, _, token = token.partition(" ")
        if schema.lower() != schema_required:
            raise AuthErrors.not_authenticated.err()
        return self.parse_token(token)

    def get_user_auth(self, token: Optional[str] = Cookie(default=None, alias='Token')) -> _Token:
        if token is None:
            raise AuthErrors.not_authenticated.err()
        return self.get_auth('bearer', token)

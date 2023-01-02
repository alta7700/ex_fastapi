from collections.abc import Callable
from typing import Any, Optional, Type

from fastapi import Cookie, Header
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

    def get_user_auth(
            self,
            cookie: bool = False,
            header: bool = False,
            schema: str = 'bearer'
    ) -> Callable[[Any], _Token]:
        assert cookie or header
        _cookie, _header = Cookie(default=None, alias='Token'), Header(default=None, alias='Token')
        if cookie and header:
            def wrapper(cookie_token: str = _cookie, header_token: str = _header) -> _Token:
                return self._get_user_auth(cookie_token or header_token, schema=schema)
        elif cookie:
            def wrapper(cookie_token: str = _cookie) -> _Token:
                return self._get_user_auth(cookie_token, schema=schema)
        else:
            def wrapper(header_token: str = _header) -> _Token:
                return self._get_user_auth(header_token, schema=schema)
        return wrapper

    def _get_user_auth(self, token: str, schema: str = 'bearer'):
        if token is None:
            raise AuthErrors.not_authenticated.err()
        return self.get_auth(schema, token)

from collections.abc import Callable
from typing import Any

from fastapi import Cookie, Header
from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError

from ex_fastapi.global_objects import get_auth_errors
from .config import BaseJWTConfig, TokenTypes, AuthStrategy, default_auth_strategy, Token, auth_strategy_is_valid


AuthErrors = get_auth_errors()


class JWTConsumer(BaseJWTConfig):
    PUBLIC_KEY: str

    def __init__(self, public_key: str):
        self.PUBLIC_KEY = public_key.strip("'").strip('"')

    def decode(self, token: str) -> dict[str, Any]:
        return self.jwt.decode(token, self.PUBLIC_KEY, [self.ALGORITHM])


class AuthConsumer:

    jwt: JWTConsumer
    auth_method: str
    auth_schema: str

    def __init__(self, public_key: str, strategy: AuthStrategy):
        self.jwt = JWTConsumer(public_key)
        strategy: AuthStrategy = {**default_auth_strategy, **strategy}
        assert auth_strategy_is_valid(strategy)
        self.auth_method = strategy['method']
        self.auth_schema = strategy['schema']

    def get_token_payload(self, token: str):
        try:
            payload = self.jwt.decode(token)
        except (InvalidSignatureError, DecodeError):
            raise AuthErrors.invalid_token.err()
        except ExpiredSignatureError:
            raise AuthErrors.expired_token.err()
        return Token(**payload)

    def parse_token(self, token: str, token_type: TokenTypes) -> "Token":
        payload = self.get_token_payload(token)
        if payload.type != token_type:
            raise AuthErrors.not_authenticated.err()
        return payload

    def get_auth(self, token: str, token_type: TokenTypes) -> "Token":
        if token is None:
            raise AuthErrors.not_authenticated.err()
        schema, _, token = token.partition(" ")
        if schema.lower() != self.auth_schema:
            raise AuthErrors.not_authenticated.err()
        return self.parse_token(token, token_type=token_type)

    def get_user_auth(self) -> Callable[[Any], "Token"]:
        if self.auth_method == 'cookie':
            def wrapper(cookie_token: str = Cookie(default=None, alias='Token')) -> "Token":
                return self.get_auth(cookie_token, TokenTypes.access)
        else:
            def wrapper(header_token: str = Header(default=None, alias='Token')) -> "Token":
                return self.get_auth(header_token, TokenTypes.access)
        return wrapper

    def get_refresh_token(self, token: str) -> "Token":
        return self.get_auth(token, TokenTypes.access)

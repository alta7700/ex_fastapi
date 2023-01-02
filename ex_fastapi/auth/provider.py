from datetime import timedelta, datetime
from typing import Any, Type

from ex_fastapi import CamelModel
from ex_fastapi.default_response import DefaultJSONEncoder
from .schemas import _TokenIssue, _TokenPair
from .config import BaseJWTConfig, TokenTypes


LIFETIME = dict[TokenTypes, int]
lifetime_default: LIFETIME = {
    TokenTypes.access: int(timedelta(minutes=5).total_seconds()),
    TokenTypes.refresh: int(timedelta(days=10).total_seconds()),
}


class JWTProvider(BaseJWTConfig):
    lifetime: LIFETIME
    PRIVATE_KEY: str
    json_encoder = DefaultJSONEncoder

    def __init__(self, private_key: str, lifetime: LIFETIME = None):
        self.lifetime = {**lifetime_default, **(lifetime or {})}
        self.PRIVATE_KEY = private_key.replace('|||n|||', '\n').strip("'").strip('"')

    def encode(self, payload: dict[str, Any]) -> str:
        return self.jwt.encode(payload, self.PRIVATE_KEY, self.ALGORITHM, json_encoder=self.json_encoder)


class AuthProvider:
    jwt: JWTProvider

    def __init__(
            self,
            token_user: Type[CamelModel],
            user_me_read: Type[CamelModel],
            private_key: str,
            lifetime: LIFETIME = None,
    ):
        assert token_user.__config__.orm_mode and user_me_read.__config__.orm_mode
        self.TokenIssue = _TokenIssue[token_user]
        self.TokenPair = _TokenPair[user_me_read]
        self.jwt = JWTProvider(private_key, lifetime=lifetime)

    @staticmethod
    def now() -> int:
        return int(datetime.now().timestamp())

    def create_token(self, user, token_type: TokenTypes, now: int = None) -> str:
        return self.jwt.encode(
            self.TokenIssue(user=user, type=token_type, iat=now or self.now(), lifetime=self.jwt.lifetime).dict()
        )

    def create_access_token(self, user, now: int = None) -> str:
        return self.create_token(user, TokenTypes.access, now)

    def create_refresh_token(self, user, now: int = None) -> str:
        return self.create_token(user, TokenTypes.refresh, now)

    def get_user_token_pair(self, user) -> _TokenPair:
        now = self.now()
        return self.TokenPair(
            access_token=self.create_access_token(user, now=now),
            refresh_token=self.create_refresh_token(user, now=now),
            user=user
        )

from datetime import timedelta, datetime
from typing import Any

from fastapi import Response

from ex_fastapi.default_response import DefaultJSONEncoder
from ex_fastapi.schemas import TokenIssue, TokenPair
from ex_fastapi.settings import get_settings_obj
from .config import BaseJWTConfig, TokenTypes


LIFETIME = dict[TokenTypes, int]
lifetime_default: LIFETIME = {
    TokenTypes.access: int(timedelta(minutes=5).total_seconds()),
    TokenTypes.refresh: int(timedelta(days=10).total_seconds()),
}
settings_obj = get_settings_obj()
COOKIE_SECURE = settings_obj.COOKIE_SECURE


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

    def __init__(self, private_key: str, lifetime: LIFETIME = None):
        self.jwt = JWTProvider(private_key, lifetime=lifetime)

    @staticmethod
    def now() -> int:
        return int(datetime.now().timestamp())

    def create_token(self, user, token_type: TokenTypes, now: int = None) -> str:
        return self.jwt.encode(
            TokenIssue(user=user, type=token_type, iat=now or self.now(), lifetime=self.jwt.lifetime).dict()
        )

    def create_access_token(self, user, now: int = None) -> str:
        return self.create_token(user, TokenTypes.access, now)

    def create_refresh_token(self, user, now: int = None) -> str:
        return self.create_token(user, TokenTypes.refresh, now)

    def get_user_token_pair(self, user) -> TokenPair:
        now = self.now()
        return TokenPair(
            access_token=self.create_access_token(user, now=now),
            refresh_token=self.create_refresh_token(user, now=now),
            user=user
        )

    def set_auth_cookie(self, response: Response, user):
        access_token = self.create_access_token(user)
        response.set_cookie(
            key='Token', value="Bearer " + access_token,
            path='/api', max_age=self.jwt.lifetime[TokenTypes.access],
            httponly=True, secure=COOKIE_SECURE
        )

    @classmethod
    def delete_auth_cookie(cls, response: Response):
        response.delete_cookie(key='Token', path='/api', httponly=True, secure=COOKIE_SECURE)

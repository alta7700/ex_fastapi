from datetime import timedelta, datetime
from typing import Any

from fastapi import Response
from pydantic import root_validator

from ex_fastapi.default_response import DefaultJSONEncoder
from ex_fastapi.settings import get_settings_obj
from ex_fastapi.pydantic import CamelModel
from ex_fastapi.pydantic.utils import get_schema
from ex_fastapi.schemas import UserMeRead
from .config import BaseJWTConfig, TokenTypes, AuthStrategy, default_auth_strategy, Token, auth_strategy_is_valid


UserMeRead = get_schema(UserMeRead)


class TokenIssue(Token):
    exp: int  # timestamp

    @root_validator(pre=True)
    def calc_ext(cls, values: dict[str, Any]) -> dict[str, Any]:
        if 'exp' not in values:
            seconds = values['lifetime'][values['type']]
            values["exp"] = values["iat"] + seconds
        return values


class TokenPair(CamelModel):
    access_token: str
    refresh_token: str
    user: UserMeRead


LIFETIME = dict[TokenTypes, int]
lifetime_default: LIFETIME = {
    TokenTypes.access: int(timedelta(minutes=5).total_seconds()),
    TokenTypes.refresh: int(timedelta(days=10).total_seconds()),
}
COOKIE_SECURE = get_settings_obj().cookie_secure


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
    auth_method: str
    auth_schema: str

    def __init__(self, private_key: str, strategy: AuthStrategy, lifetime: LIFETIME = None):
        self.jwt = JWTProvider(private_key, lifetime=lifetime)
        strategy: AuthStrategy = {**default_auth_strategy, **strategy}
        assert auth_strategy_is_valid(strategy)
        self.auth_method = strategy['method']
        self.auth_schema = strategy['schema']

    @staticmethod
    def now() -> int:
        return int(datetime.now().timestamp())

    def create_token(self, user, token_type: TokenTypes, now: int = None) -> str:
        return self.jwt.encode(
            TokenIssue(
                user=user,
                type=token_type,
                iat=now or self.now(),
                lifetime=self.jwt.lifetime
            ).dict()
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
        response.set_cookie(
            key='Token', value=f'{self.auth_schema.title()} {self.create_access_token(user)}',
            path='/api', max_age=self.jwt.lifetime[TokenTypes.access],
            httponly=True, secure=COOKIE_SECURE
        )

    def authorize(self, response: Response, user) -> Any:
        if self.auth_method == 'cookie':
            self.set_auth_cookie(response, user)
            return UserMeRead.from_orm(user)
        else:
            return self.get_user_token_pair(user)

    @property
    def authorize_response_model(self):
        if self.auth_method == 'cookie':
            return UserMeRead
        else:
            return TokenPair

    @classmethod
    def delete_auth_cookie(cls, response: Response):
        response.delete_cookie(key='Token', path='/api', httponly=True, secure=COOKIE_SECURE)

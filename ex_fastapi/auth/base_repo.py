from typing import Type, TypeVar, Generic

from fastapi import Response
from passlib.context import CryptContext

from ex_fastapi.auth.schemas import PasswordsPair


USER = TypeVar("USER")


class BaseUserRepository(Generic[USER]):
    model: Type[USER]
    user: USER
    pwd_context = CryptContext(schemes=["md5_crypt"])

    def __init__(self, user):
        self.user = user

    @classmethod
    async def create_user(cls, data: PasswordsPair, **kwargs) -> USER:
        raise NotImplementedError

    def set_password(self, password: str) -> None:
        raise NotImplementedError

    def get_fake_password(self, password: str) -> str:
        raise NotImplementedError

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(self.get_fake_password(password))

    def verify_password(self, password: str) -> bool:
        return self.pwd_context.verify(self.get_fake_password(password), self.user.password_hash)

    @property
    def save(self):
        raise NotImplementedError

    @classmethod
    def get_user_by(cls, field: str, value: str | int):
        raise NotImplementedError

    @classmethod
    async def email_exists(cls, email: str) -> bool:
        return await cls.get_user_by('email', email) is not None

    @classmethod
    async def phone_exists(cls, phone: str) -> bool:
        return await cls.get_user_by('phone', phone) is not None

    @classmethod
    async def username_exists(cls, username: str) -> bool:
        return await cls.get_user_by('username', username) is not None

    async def login(self, response: Response):
        raise NotImplementedError

    async def get_permissions(self):
        raise NotImplementedError

    async def has_permissions(self, *perms):
        raise NotImplementedError

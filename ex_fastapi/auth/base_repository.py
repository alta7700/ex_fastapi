from typing import Type, Generic, TypeVar

from passlib.context import CryptContext

from ex_fastapi.schemas import PasswordsPair


USER_MODEL = TypeVar("USER_MODEL")


class BaseUserRepository(Generic[USER_MODEL]):
    model: Type[USER_MODEL]
    user: USER_MODEL
    pwd_context = CryptContext(schemes=["md5_crypt"])

    def __init__(self, user):
        self.user = user

    @classmethod
    async def create_user(cls, data: PasswordsPair, should_exclude: set[str] = None, **kwargs) -> USER_MODEL:
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

    async def can_login(self):
        raise NotImplementedError

    def get_permissions(self):
        raise NotImplementedError

    def has_permissions(self, *perms):
        raise NotImplementedError

from random import choices
from string import hexdigits
from typing import Type, TypeVar

from passlib.context import CryptContext
from tortoise import timezone
from tortoise.queryset import QuerySetSingle

from ex_fastapi.auth.base_repo import BaseUserRepository
from ex_fastapi.auth.schemas import PasswordsPair
from .. import get_user_model, max_len_of
from ..models import BaseUser, Permission

USER = TypeVar("USER", bound=BaseUser)
user_model = get_user_model()


class UserRepository(BaseUserRepository[USER]):
    model: Type[USER] = user_model
    user: USER
    pwd_context = CryptContext(schemes=["md5_crypt"])

    @classmethod
    async def create_user(cls, data: PasswordsPair, should_exclude: set[str], **kwargs) -> USER:
        self = cls(cls.model(**data.dict(exclude={'password', 're_password', *should_exclude}), **kwargs))
        self.set_password(data.password)
        return self.user

    def set_password(self, password: str) -> None:
        user = self.user
        user.password_change_dt = timezone.now()
        user.password_salt = ''.join(choices(hexdigits, k=max_len_of(self.model)('password_salt')))
        user.password_hash = self.get_password_hash(password or ''.join(choices(hexdigits, k=30)))
        if not password:
            user.password_hash = '!' + user.password_hash

    def get_fake_password(self, password: str) -> str:
        user = self.user
        return password + str(user.password_change_dt.timestamp()) + user.password_salt

    @property
    def save(self):
        return self.user.save

    @classmethod
    def get_user_by(cls, field: str, value: str | int) -> QuerySetSingle["USER"]:
        if field in cls.model.IEXACT_FIELDS:
            field += '__iexact'
        return cls.model.get_or_none(**{field: value})

    async def can_login(self):
        return self.user.is_active

    async def get_permissions(self) -> tuple[Permission, ...]:
        return *self.user.permissions, *(p for g in self.user.groups for p in g.permissions)

    async def has_permissions(self, permissions) -> bool:
        # if not permissions:
        #     return True
        user_perms = await self.get_permissions()
        print(user_perms)
        return True

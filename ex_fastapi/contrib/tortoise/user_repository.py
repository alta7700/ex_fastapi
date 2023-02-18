from random import choices
from string import hexdigits
from typing import Type

from passlib.context import CryptContext
from tortoise import timezone
from tortoise.queryset import QuerySetSingle

from ex_fastapi.global_objects import get_user_model
from ex_fastapi.auth.base_repository import BaseUserRepository
from ex_fastapi.schemas import PasswordsPair
from ex_fastapi.models import UserWithPermissions, ContentType, max_len_of, BaseModel


class TortoiseUserRepository(BaseUserRepository[UserWithPermissions]):
    model: Type[UserWithPermissions] = get_user_model()
    user: UserWithPermissions
    pwd_context = CryptContext(schemes=["md5_crypt"])

    @classmethod
    async def create_user(cls, data: PasswordsPair, should_exclude: set[str] = None, **kwargs) -> UserWithPermissions:
        self = cls(cls.model(**data.dict(exclude={'password', 're_password', *(should_exclude or set())}), **kwargs))
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
    def get_user_by(cls, field: str, value: str | int) -> QuerySetSingle[UserWithPermissions]:
        if field in cls.model.IEXACT_FIELDS:
            field += '__iexact'
        return cls.model.get_or_none(**{field: value})

    async def can_login(self):
        return self.user.is_active

    def get_permissions(self) -> tuple[tuple[int, str], ...]:
        return tuple((perm.content_type_id, perm.name) for perm in self.user.all_permissions)

    async def has_permissions(self, permissions: tuple[tuple[Type[BaseModel], str], ...]) -> bool:
        if not permissions:
            return True
        user_perms = self.get_permissions()
        has = True
        for model, perm_name in permissions:
            content_type_id = ContentType.get_by_name(model.__name__).id
            if (content_type_id, perm_name) not in user_perms:
                has = False
                break
        return has

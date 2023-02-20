from random import choices
from string import hexdigits
from typing import Type, TypeVar, Literal
from uuid import UUID

from fastapi import BackgroundTasks
from passlib.context import CryptContext
from tortoise import timezone
from tortoise.queryset import QuerySetSingle

from ex_fastapi.global_objects import get_user_model
from ex_fastapi.auth.base_repository import BaseUserRepository
from ex_fastapi.schemas import PasswordsPair
from ex_fastapi.models import UserWithPermissions, ContentType, max_len_of, BaseModel


UNUSED_PASSWORD_PREFIX = '!'
USER_MODEL = TypeVar('USER_MODEL', bound=UserWithPermissions)


class UserRepository(BaseUserRepository[USER_MODEL]):
    model: Type[USER_MODEL] = get_user_model()
    user: USER_MODEL
    pwd_context = CryptContext(schemes=["md5_crypt"])

    @classmethod
    async def create_user(
            cls,
            data: PasswordsPair,
            should_exclude: set[str] = None,
            **kwargs
    ) -> USER_MODEL:
        self = cls(cls.model(**data.dict(exclude={'password', 're_password', *(should_exclude or set())}), **kwargs))
        self.set_password(data.password)
        await self.save(force_create=True)
        return self.user

    async def post_registration(self, background_tasks: BackgroundTasks):
        await self.user.fetch_related('permissions', 'groups__permissions')
        self.add_send_activation_email_task(background_tasks=background_tasks)

    @property
    def is_user_active(self) -> bool:
        return self.user.is_active

    @property
    def uuid(self) -> UUID:
        return self.user.uuid

    def check_temp_code_error(self, code: str) -> Literal['expired', 'incorrect'] | None:
        tc = self.user.temp_code
        if tc.expired:
            return 'expired'
        if not tc.correct(code):
            return 'incorrect'

    async def activate(self) -> None:
        self.user.is_active = True
        await self.user.temp_code.delete()
        await self.save(force_update=True)

    def set_password(self, password: str) -> None:
        user = self.user
        user.password_change_dt = timezone.now()
        user.password_salt = ''.join(choices(hexdigits, k=max_len_of(self.model)('password_salt')))
        if password:
            user.password_hash = self.get_password_hash(password)
        else:
            user.password_hash = UNUSED_PASSWORD_PREFIX + self.get_password_hash(''.join(choices(hexdigits, k=30)))

    def get_fake_password(self, password: str) -> str:
        user = self.user
        return password + str(user.password_change_dt.timestamp()) + user.password_salt

    def verify_password(self, password: str) -> bool:
        if self.user.password_hash.startswith(UNUSED_PASSWORD_PREFIX):
            return False
        return self.pwd_context.verify(self.get_fake_password(password), self.user.password_hash)

    @property
    def save(self):
        return self.user.save

    @classmethod
    def get_user_by(cls, field: str, value: UUID | str | int) -> QuerySetSingle[USER_MODEL]:
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

    async def update_or_create_temp_code(self):
        temp_code, created = await self.user.temp_code.model.get_or_create(user=self.user)
        if not created:
            await temp_code.update()
        await self.user.fetch_related('temp_code')

    async def send_activation_email(self):
        from ex_fastapi.mailing import default_mail_sender
        await self.update_or_create_temp_code()
        await default_mail_sender.activation_email(
            to=self.user.email,
            username=self.user.username,
            uuid=self.user.uuid,
            temp_code=self.user.temp_code.code,
            duration=self.user.temp_code.duration_text,
        )

    def add_send_activation_email_task(self, background_tasks: BackgroundTasks):
        if not self.user.is_active and 'temp_code' in self.user._meta.fields_map:
            background_tasks.add_task(self.send_activation_email)

from datetime import datetime
from typing import Type, Generic, TypeVar, Protocol, Optional, Literal
from uuid import UUID

from passlib.context import CryptContext
from fastapi import BackgroundTasks
from pydantic import EmailStr

from ex_fastapi.pydantic import Username, PhoneNumber
from ex_fastapi.schemas import PasswordsPair


class UserInterface(Protocol):
    id: int
    uuid: UUID
    username: Optional[Username]
    email: Optional[EmailStr]
    phone: Optional[PhoneNumber]
    password_hash: str
    password_change_dt: datetime
    password_salt: str
    is_superuser: bool
    is_active: bool
    created_at: datetime


USER_MODEL = TypeVar("USER_MODEL", bound=UserInterface)


class BaseUserRepository(Generic[USER_MODEL]):
    model: Type[USER_MODEL]
    user: USER_MODEL
    pwd_context = CryptContext(schemes=["md5_crypt"])

    def __init__(self, user):
        self.user = user

    @classmethod
    async def create_user(
            cls,
            data: PasswordsPair,
            should_exclude: set[str] = None,
            **kwargs
    ) -> USER_MODEL:
        raise NotImplementedError

    async def post_registration(self, background_tasks: BackgroundTasks):
        raise NotImplementedError

    @property
    def is_user_active(self) -> bool:
        raise NotImplementedError

    @property
    def uuid(self) -> UUID:
        raise NotImplementedError

    def check_temp_code_error(self, code: str) -> Literal['expired', 'incorrect'] | None:
        raise NotImplementedError

    async def activate(self):
        raise NotImplementedError

    def set_password(self, password: str) -> None:
        raise NotImplementedError

    def get_fake_password(self, password: str) -> str:
        raise NotImplementedError

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(self.get_fake_password(password))

    def verify_password(self, password: str) -> bool:
        raise NotImplementedError

    @property
    def save(self):
        raise NotImplementedError

    @classmethod
    def get_user_by(cls, field: str, value: UUID | str | int):
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

    async def update_or_create_temp_code(self):
        raise NotImplementedError

    async def send_activation_email(self):
        raise NotImplementedError

    def add_send_activation_email_task(self, background_tasks: BackgroundTasks):
        raise NotImplementedError

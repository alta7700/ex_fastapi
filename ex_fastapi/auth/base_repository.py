from typing import Type, Generic, TypeVar, Protocol, Optional, Literal, TYPE_CHECKING, Any
from datetime import datetime
from uuid import UUID

from passlib.context import CryptContext
from fastapi import BackgroundTasks
from pydantic import EmailStr

from ex_fastapi.pydantic import Username, PhoneNumber
from ex_fastapi.schemas import PasswordsPair

if TYPE_CHECKING:
    from .config import Token


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
    AUTH_FIELDS: tuple[str, ...]


USER_MODEL = TypeVar("USER_MODEL", bound=UserInterface)


class BaseUserRepository(Generic[USER_MODEL]):
    model: Type[USER_MODEL]
    user: USER_MODEL
    pwd_context = CryptContext(schemes=["md5_crypt"])

    def __init__(self, user: USER_MODEL):
        self.user = user

    @classmethod
    async def create_user(
            cls,
            data: PasswordsPair,
            should_exclude: set[str] = None,
            defaults: dict[str, Any] = None
    ) -> USER_MODEL:
        raise NotImplementedError

    async def post_registration(self, background_tasks: BackgroundTasks) -> None:
        raise NotImplementedError

    @property
    def pk(self) -> int | UUID:
        raise NotImplementedError

    @property
    def is_user_active(self) -> bool:
        raise NotImplementedError

    @property
    def is_superuser(self) -> bool:
        raise NotImplementedError

    @property
    def uuid(self) -> UUID:
        raise NotImplementedError

    def check_temp_code_error(self, code: str) -> Literal['expired', 'incorrect'] | None:
        raise NotImplementedError

    async def activate(self) -> None:
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

    def can_login(self) -> bool:
        raise NotImplementedError

    def token_expired(self, token: "Token") -> bool:
        raise NotImplementedError

    def get_permissions(self) -> tuple[tuple[int, str], ...]:
        raise NotImplementedError

    def has_permissions(self, *perms) -> bool:
        raise NotImplementedError

    async def update_or_create_temp_code(self) -> None:
        raise NotImplementedError

    async def send_activation_email(self) -> None:
        raise NotImplementedError

    def add_send_activation_email_task(self, background_tasks: BackgroundTasks) -> None:
        raise NotImplementedError

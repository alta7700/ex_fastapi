from typing import Literal, Optional, Any, Type
from datetime import datetime

from tortoise import fields
from pydantic import EmailStr
from ex_fastapi.pydantic import Username, PhoneNumber

from .. import Model
from . import PermissionMixin


__all__ = ["BaseUser", "UserWithPermissions"]

USER_GET_BY_FIELDS = Literal['id', 'email', 'username', 'phone']


class BaseUser(Model):
    id: int
    username: Optional[Username] = fields.CharField(max_length=40, unique=True, null=True)
    email: Optional[EmailStr] = fields.CharField(max_length=256, unique=True, null=True)
    phone: Optional[PhoneNumber] = fields.CharField(max_length=25, unique=True, null=True)
    AUTH_FIELDS = ('email', 'phone', 'username')
    IEXACT_FIELDS = ('email', 'username')

    password_hash: str = fields.CharField(max_length=200)
    password_change_dt: datetime = fields.DatetimeField()
    password_salt: str = fields.CharField(max_length=50)

    is_superuser: bool = fields.BooleanField(default=False)
    is_active: bool = fields.BooleanField(default=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def repr(self) -> str:
        return self.username or self.email or self.phone


class UserWithPermissions(BaseUser, PermissionMixin):
    class Meta:
        abstract = True

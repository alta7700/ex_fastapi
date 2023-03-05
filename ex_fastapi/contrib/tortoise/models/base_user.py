import random
from string import ascii_uppercase, digits
from typing import Literal, Optional, Union, Sequence
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from tortoise import fields, timezone
from pydantic import EmailStr

from ex_fastapi.global_objects import get_user_model_path
from ex_fastapi.pydantic import Username, PhoneNumber

from . import BaseModel, PermissionMixin


USER_GET_BY_FIELDS = Literal['id', 'email', 'username', 'phone']


class BaseUser(BaseModel):
    id: int
    uuid: UUID = fields.UUIDField(default=uuid4, unique=True)
    username: Optional[Username] = fields.CharField(max_length=40, unique=True, null=True)
    email: Optional[EmailStr] = fields.CharField(max_length=256, unique=True, null=True)
    phone: Optional[PhoneNumber] = fields.CharField(max_length=25, unique=True, null=True)
    AUTH_FIELDS = ('email', 'phone', 'username')
    IEXACT_FIELDS = ('email', 'username')
    EMAIL_FIELD = 'email'

    password_hash: str = fields.CharField(max_length=200)
    password_change_dt: datetime = fields.DatetimeField()
    password_salt: str = fields.CharField(max_length=50)

    is_superuser: bool = fields.BooleanField(default=False)
    is_active: bool = fields.BooleanField(default=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    temp_code: Union["BaseTempCode", fields.BackwardOneToOneRelation["BaseTempCode"]]

    class Meta:
        abstract = True

    def repr(self) -> str:
        return self.username or self.email or self.phone

    @classmethod
    def get_queryset_select_related(cls, path: str, method: str) -> set[str]:
        sr = super().get_queryset_select_related(path, method)
        if path.endswith('/activation'):
            sr.add('temp_code')
        return sr


class UserWithPermissions(BaseUser, PermissionMixin):
    class Meta:
        abstract = True


TEMP_CODE_LEN: int = 6


def get_random_tempcode() -> str:
    return ''.join(random.choices(ascii_uppercase + digits, k=TEMP_CODE_LEN))


class BaseTempCode(BaseModel):
    id: int = fields.BigIntField(pk=True)
    user: UserWithPermissions | fields.OneToOneRelation[UserWithPermissions] = fields.OneToOneField(
        get_user_model_path(), related_name='temp_code', on_delete=fields.CASCADE
    )
    code: str = fields.CharField(max_length=TEMP_CODE_LEN, default=get_random_tempcode)
    dt: datetime = fields.DatetimeField(auto_now=True)
    duration = timedelta(hours=1)
    duration_text = '1 hour'

    async def update(self):
        self.code = get_random_tempcode()
        self.dt = timezone.now()
        await self.save(force_update=True, update_fields=('code', 'dt'))

    @property
    def expired(self) -> bool:
        return self.dt > timezone.now()

    @property
    def expired_at(self) -> datetime:
        return self.dt + self.duration

    def correct(self, code: str) -> bool:
        return code == self.code

    class Meta:
        abstract = True

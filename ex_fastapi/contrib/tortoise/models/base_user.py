from tortoise import fields

from .. import Model
from . import PermissionMixin


USER_GET_BY_FIELDS = Literal['id', 'email', 'username', 'phone']


class User(Model):
    id: int
    username: Optional[Username] = fields.CharField(max_length=40, unique=True, null=True, description='Логин')
    email: Optional[EmailStr] = fields.CharField(max_length=256, unique=True, null=True, description='Почта')
    phone: Optional[PhoneNumber] = fields.CharField(max_length=25, unique=True, null=True, description='Телефон')

    password_hash: str = fields.CharField(max_length=200)
    password_change_dt: datetime = fields.DatetimeField()
    password_salt: str = fields.CharField(max_length=50)

    is_superuser: bool = fields.BooleanField(default=False, description='Суперпользователь')
    is_active: bool = fields.BooleanField(default=True, description='Активный')
    created_at: datetime = fields.DatetimeField(auto_now_add=True, description='Создан')

    class Meta:
        abstract = True

    def repr(self) -> str:
        """Пользователь"""
        return self.username or self.email or self.phone


class UserWithPermissions(User, PermissionMixin):
    class Meta:
        abstract = True

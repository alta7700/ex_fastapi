from datetime import datetime
from typing import Any, Optional

from pydantic import root_validator, validator, EmailStr, Field

from ex_fastapi.pydantic import CamelModel, CamelModelORM, Password, Username, PhoneNumber, RelatedList
from ex_fastapi.models import max_len_of, default_of
from ex_fastapi.global_objects import get_user_model
from ex_fastapi.schemas import PermissionIDS, PermissionGroupRead, PermissionRead


__all__ = [
    "PasswordsPair", "BaseAuthSchema", "AuthSchema", "UserBase",
    "UserRead", "UserMeRead", "UserEdit", "UserMeEdit", "UserCreate", "UserRegistration",
    "TokenUser",
]
User = get_user_model()


class PasswordsPair(CamelModel):
    password: Password
    re_password: str

    @validator('re_password')
    def passwords_equal(cls, v: str, values: dict[str, Any]):
        if pw := values.get('password'):
            if v != pw:
                raise ValueError("passwordsMismatch")
        return v


class BaseAuthSchema(CamelModel):
    login: Optional[str]
    password: str

    @root_validator
    def what_is(cls, values: dict[str, Any]):
        if login_value := values.get('login'):
            for field_name in cls.__config__.auth_fields:
                try:
                    value = cls.__fields__[field_name].type_.validate(login_value)
                    values[field_name] = value
                    break
                except ValueError:
                    pass
        else:
            if not any(x in values for x in cls.__config__.auth_fields):
                raise ValueError('No valid email, phone or username for sign in')
        return values

    def get_auth_field_and_value(self) -> tuple[str, Any]:
        for f in self.__config__.auth_fields:
            if value := getattr(self, f):
                return f, value  # type: ignore
        raise Exception('Это что такое')

    class Config(CamelModel.Config):
        extra = 'allow'
        auth_fields = ()


class UserBase(CamelModel):
    username: Optional[Username] = Field(max_length=max_len_of(User)('username'))
    email: Optional[EmailStr]
    phone: Optional[PhoneNumber]


class AuthSchema(UserBase, BaseAuthSchema):
    username: Optional[str] = Field(max_length=max_len_of(User)('username'))

    class Config(BaseAuthSchema.Config):
        auth_fields = User.AUTH_FIELDS


class UserReadBase(UserBase):
    id: int
    username: Optional[str]
    is_active: bool
    created_at: datetime

    class Config(UserBase.Config):
        orm_mode = True


class UserRead(UserReadBase):
    permissions: PermissionIDS
    groups: RelatedList[PermissionGroupRead]


class UserMeRead(UserReadBase):
    all_permissions: RelatedList[PermissionRead]
    is_superuser: bool


class UserEdit(UserBase):
    permissions: Optional[list[int]]
    groups: Optional[list[int]]
    is_superuser: Optional[bool]
    is_active: Optional[bool]


class UserMeEdit(UserBase):
    pass


class UserCreate(PasswordsPair, UserBase):
    permissions: list[int]
    groups: list[int]
    is_superuser: Optional[bool] = Field(default=default_of(User)('is_superuser'))
    is_active: Optional[bool] = Field(default=default_of(User)('is_active'))


class UserRegistration(PasswordsPair, UserBase):
    pass


class TokenUser(CamelModelORM):
    id: int
    is_superuser: bool

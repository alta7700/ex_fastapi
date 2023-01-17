from datetime import datetime
from typing import Generic, TypeVar, Any, Optional, Literal, Type

from pydantic import root_validator, validator, EmailStr, Field

from ex_fastapi.pydantic import CamelModel, Password, Username, PhoneNumber
from ex_fastapi.pydantic.camel_model import CamelGeneric
from .config import TokenTypes

USER = TypeVar('USER', bound=CamelModel)


class _Token(CamelGeneric, Generic[USER]):
    type: TokenTypes
    user: USER
    iat: int  # timestamp


class _TokenIssue(CamelGeneric, Generic[USER]):
    type: TokenTypes
    user: USER
    iat: int  # timestamp
    exp: int  # timestamp

    @root_validator(pre=True)
    def calc_ext(cls, values: dict[str, Any]) -> dict[str, Any]:
        if 'exp' not in values:
            seconds = values['lifetime'][values['type']]
            values["exp"] = values["iat"] + seconds
        return values


class _TokenPair(CamelGeneric, Generic[USER]):
    access_token: str
    refresh_token: str
    user: USER


class PasswordsPair(CamelModel):
    password: Password
    re_password: str

    @validator('re_password')
    def passwords_equal(cls, v: str, values: dict[str, Any]):
        if pw := values.get('password'):
            if v != pw:
                raise ValueError("Пароли не совпадают")
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
        print(values)
        return values

    def get_auth_field_and_value(self) -> tuple[str, Any]:
        for f in self.__config__.auth_fields:
            if value := getattr(self, f):
                return f, value  # type: ignore
        raise Exception('Это что такое')

    class Config(CamelModel.Config):
        extra = 'allow'
        auth_fields = ()


USER_SCHEMA = Literal[
    "UserMeRead", "UserRead", "UserEdit", "UserCreate",
    "UserO2ORead", "UserO2OEdit", "UserO2OCreate",
    "AuthSchema", "TokenUser"
]
default_schemas: dict[USER_SCHEMA, Type[CamelModel]] = {}


def set_user_default_schemas():
    # TODO: что-то придумать, чтобы избавиться от импорта
    from ex_fastapi.contrib.tortoise import max_len_of, default_of, get_user_model
    user_model = get_user_model()

    class UserBase(CamelModel):
        username: Optional[Username] = Field(max_length=max_len_of(user_model)('username'))
        email: Optional[EmailStr]
        phone: Optional[PhoneNumber]

    class AuthSchema(UserBase, BaseAuthSchema):
        username: Optional[str] = Field(max_length=max_len_of(user_model)('username'))

        class Config(BaseAuthSchema.Config):
            auth_fields = user_model.AUTH_FIELDS

    class UserO2ORead(UserBase):
        username: Optional[str]
        id: int
        created_at: datetime

        class Config(UserBase.Config):
            orm_mode = True

    class UserRead(UserO2ORead):
        is_superuser: bool
        is_active: bool

    UserMeRead = UserRead
    UserO2OEdit = UserBase

    class UserO2OCreate(PasswordsPair, UserBase):
        password: Optional[Password]
        re_password: Optional[str]

    class UserEdit(UserBase):
        is_superuser: Optional[bool]
        is_active: Optional[bool]

    class UserCreate(PasswordsPair, UserBase):
        is_superuser: Optional[bool] = Field(default=default_of(user_model)('is_superuser'))
        is_active: Optional[bool] = Field(default=default_of(user_model)('is_active'))

    class TokenUser(CamelModel):
        id: int
        is_superuser: bool

        class Config(CamelModel.Config):
            orm_mode = True

    default_schemas.update({
        "UserMeRead": UserMeRead,
        "UserRead": UserRead,
        "UserEdit": UserEdit,
        "UserCreate": UserCreate,
        "UserO2ORead": UserO2ORead,
        "UserO2OEdit": UserO2OEdit,
        "UserO2OCreate": UserO2OCreate,
        "AuthSchema": AuthSchema,
        "TokenUser": TokenUser,
    })


def get_user_default_schema(schema_name: USER_SCHEMA):
    if not default_schemas:
        set_user_default_schemas()
    return default_schemas[schema_name]

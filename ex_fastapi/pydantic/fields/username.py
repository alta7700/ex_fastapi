import re
from typing import Any

from pydantic.validators import strict_str_validator


class Username(str):

    pattern = re.compile(r'^(?!user-)(?=.*[a-zA-Z])[\w+.+-]+$')

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        field_schema.update(type='string', format='username', example='sasha_molodez')

    @classmethod
    def __get_validators__(cls):
        yield strict_str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        if cls.pattern.match(v) is None:
            raise ValueError('Username is invalid')
        return cls(v)

import re
from typing import Any

from pydantic.validators import strict_str_validator


class Password(str):

    pattern = re.compile(r'(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-])^[a-zA-Z0-9#?!@$%^&*-]{8,30}$')

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        field_schema.update(type='string', format='password', example='!VeryStrongPassword123!')

    @classmethod
    def __get_validators__(cls):
        yield strict_str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        password = v.strip()
        if len(password) < 8:
            raise ValueError('shortPassword')
        if len(password) > 30:
            raise ValueError('longPassword')
        if not cls.pattern.match(password):
            # Incorrect password. Minimum 1 uppercase, 1 lowercase, 1 digit and 1 symbol (#?!@$%^&*-)
            raise ValueError('incorrectPassword')
        return cls(password)

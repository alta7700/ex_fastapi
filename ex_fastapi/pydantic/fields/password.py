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
            raise ValueError('Слишком короткий пароль (минимум 8)')
        if len(password) > 30:
            raise ValueError('Слишком длинный пароль (максимум 30)')
        if not cls.pattern.match(password):
            raise ValueError('Некорректный пароль, Минимум одна заглавная, прописная, цифра и спецсимвол (#?!@$%^&*-)')
        return cls(password)

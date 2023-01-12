from typing import Any

import phonenumbers

from pydantic.validators import strict_str_validator


class PhoneNumber(str):
    """Phone Number Pydantic type, using google's phonenumbers"""

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        field_schema.update(type='string', format='phone', example='89181234567')

    @classmethod
    def __get_validators__(cls):
        yield strict_str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        try:
            pn = phonenumbers.parse(v.replace(' ', ''), region='RU')
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValueError('invalid phone number format')
        return cls(phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164))

from enum import Enum
from typing import Any, TypeVar, Type


class _FieldInRelatedModelInstance:

    _related: Any
    _field: str
    _type: Any

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, cls):
            return v
        if not isinstance(v, cls._related):
            raise ValueError(
                f'Related class is not instance of {getattr(cls._related, "__class__", "related_class")}. '
                f'Type is {type(v)}'
            )
        value = getattr(v, cls._field)
        if not isinstance(value, cls._type):
            raise ValueError(
                f'{getattr(v, "__class__", "related_class")}.{cls._field} = '
                f'{value} is {type(value)}, not {cls._type.__name__}'
            )
        return value


_T = TypeVar('_T')


def FieldInRelatedModel(
        related_class: Any,
        field_name: str,
        value_type: _T,
        modify_schema: dict[str, Any] = None,
) -> _T:

    class BaseWrapped(_FieldInRelatedModelInstance):
        _related = related_class
        _field = field_name
        _type = value_type

    if issubclass(value_type, Enum):
        modify_schema = modify_schema or {'type': {"anyOf": [{"type": "string"}, {"type": "integer"}]}}

        class Wrapped(BaseWrapped):
            @classmethod
            def __modify_schema__(cls, field_schema):
                for key, value in modify_schema.items():
                    field_schema[key] = value

            @classmethod
            def validate(cls, v):
                if isinstance(v, Enum):
                    return v
                return super().validate(v)
    else:
        class Wrapped(value_type, BaseWrapped):

            if modify_schema:
                @classmethod
                def __modify_schema__(cls, field_schema):
                    for key, value in modify_schema.items():
                        field_schema[key] = value

            @classmethod
            def validate(cls, v):
                return cls(super().validate(v))  # type: ignore

    return Wrapped

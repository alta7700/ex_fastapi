from typing import Self, Generic, TypeVar, Type, TypedDict, Any

from starlette.datastructures import QueryParams

from ex_fastapi import lower_camel

DB_QUERY_CLS = TypeVar('DB_QUERY_CLS')
VALUE_TYPE = TypeVar('VALUE_TYPE')
OPTS = TypeVar('OPTS', bound=TypedDict)
VALIDATOR = TypeVar('VALIDATOR', bound="BaseFilterValidator")


class BaseFilter(Generic[VALUE_TYPE, OPTS, VALIDATOR]):
    value: VALUE_TYPE | None
    error = Exception | None
    base_validator: VALIDATOR
    validator: VALIDATOR
    field_name: str
    camel_source: str
    suffix: str = ''

    def __init__(self, value: VALUE_TYPE | None, error: Exception | None):
        self.value = value
        self.error = error

    @classmethod
    def create(cls, field_name: str, validator_opts: OPTS = None) -> Type[Self]:
        source = field_name + cls.suffix
        final_cls: cls = type(  # type: ignore
            cls.__name__ + source.title(),
            (cls,),
            {
                'field_name': field_name,
                'camel_source': lower_camel(source),
                'validator': cls.create_validator(validator_opts or {}),
            }
        )
        return final_cls

    @classmethod
    def create_validator(cls, opts: OPTS) -> Type["BaseFilterValidator"]:
        return cls.base_validator.apply_opts(opts)

    @classmethod
    def from_qs(cls, query_params: QueryParams) -> Self:
        value = query_params.get(cls.camel_source)
        error = None
        if value is not None:
            try:
                value = cls.validator.validate(value)
            except ValueError as e:
                value = None
                error = e
        return cls(value, error)

    def filter(self, query: DB_QUERY_CLS) -> DB_QUERY_CLS:
        raise NotImplemented

    def __bool__(self):
        return getattr(self, 'value', None) is not None or getattr(self, 'error', None) is not None

    @classmethod
    def describe(cls):
        return cls.__doc__

    @classmethod
    def query_openapi_desc(cls):
        cls.base_validator.__modify_schema__(schema := {})
        return {
            "required": False,
            "schema": {
                "title": cls.camel_source,
                **schema
            },
            'description': cls.describe(),
            'name': cls.camel_source,
            'in': 'query',
        }


class BaseFilterValidator(Generic[OPTS]):

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        field_schema.update(**cls.__schema__())

    @classmethod
    def __schema__(self) -> dict[str, Any]:
        return {"type": 'string', 'example': 'AnyString'}

    @classmethod
    def apply_opts(cls, opts: OPTS) -> Type[Self]:
        return type(cls.__name__, (cls,), opts)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> Self:
        raise NotImplemented

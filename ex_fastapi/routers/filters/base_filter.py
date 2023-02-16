from typing import Self, Generic, TypeVar, Type, TypedDict

from starlette.datastructures import QueryParams

from ex_fastapi import lower_camel

DB_QUERY_CLS = TypeVar('DB_QUERY_CLS')
VALUE_TYPE = TypeVar('VALUE_TYPE')
OPTS = TypeVar('OPTS', bound=TypedDict)


class BaseFilter(Generic[VALUE_TYPE, OPTS]):

    value: VALUE_TYPE
    base_validator: Type["BaseFilterValidator"]
    validator: Type["BaseFilterValidator"]
    source: str
    camel_source: str
    suffix: str = ''

    def __init__(self, value: VALUE_TYPE):
        self.value = value

    @classmethod
    def create(cls, source: str, validator_opts: OPTS = None) -> Type[Self]:
        source = source + cls.suffix
        final_cls: cls = type(  # type: ignore
            cls.__name__ + source.title(),
            (cls,),
            {
                'source': source,
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
        if value is not None:
            value = cls.validator.validate(value)
        return cls(value)

    def filter(self, query: DB_QUERY_CLS) -> DB_QUERY_CLS:
        raise NotImplemented

    def __bool__(self):
        return getattr(self, 'value', None) is not None


class BaseFilterValidator(Generic[OPTS]):

    @classmethod
    def apply_opts(cls, opts: OPTS) -> Type[Self]:
        return type(cls.__name__, (cls,), opts)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> Self:
        raise NotImplemented

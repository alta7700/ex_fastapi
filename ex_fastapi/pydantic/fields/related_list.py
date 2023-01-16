from collections.abc import Iterable

from tortoise.exceptions import NoValuesFetched


class _Related:

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, Iterable):
            raise ValueError(f'{v} is not Iterable')
        try:
            value = [*v]
        except NoValuesFetched as e:
            raise ValueError(e)
        return cls(value)


class RelatedList(_Related, list):
    pass


class RelatedSet(_Related, set):
    pass

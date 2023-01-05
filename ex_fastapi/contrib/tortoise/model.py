from collections.abc import Callable
from typing import Any, Type

from tortoise import Model as DefaultModel


class Model(DefaultModel):

    class Meta:
        abstract = True


def get_field(model: Type[Model], fname: str):
    return model._meta.fields_map[fname]


def max_len_of(model: Type[Model]) -> Callable[[str], int]:
    def wrapper(fname: str):
        return get_field(model, fname).max_length
    return wrapper


def default_of(model: Type[Model]) -> Callable[[str], Any]:
    def wrapper(fname: str):
        return get_field(model, fname).default
    return wrapper

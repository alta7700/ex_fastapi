from typing import TypeVar, Any, Callable, Type, Self

T = TypeVar('T')


def CommaSeparatedOf(
        t: Type[T],
        wrapper: Callable[[str], T] = None,  # function for converting item
        modify: dict[str, Any] = None,
        transform_initial_str: Callable[[str], str] = None,
        max_items: int = None,
        min_items: int = None,
        in_query: bool = False
) -> Type[list[T]]:

    wrapper = wrapper or t
    if in_query and transform_initial_str is None:
        def transform_initial_str(x: list[str]):
            return x[0]

    modify = modify or {}

    class CommaSeparatedT(list[T]):

        item_type = t

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def __modify_schema__(cls, field_schema):
            field_schema.update(
                type='string',
                **modify
            )

        def check_len(self):
            if min_items or max_items:
                _len = len(self)
                if min_items and _len < min_items:
                    raise ValueError(f'Minimum {min_items} values')
                if max_items and _len > max_items:
                    raise ValueError(f'Maximum {max_items} values')
            return self

        @classmethod
        def validate(cls, v: str | list[str]) -> Self:
            if transform_initial_str:
                v = transform_initial_str(v)
            if not isinstance(v, str):
                raise ValueError('value must be str')
            return cls(map(wrapper, v.split(','))).check_len()

    return CommaSeparatedT

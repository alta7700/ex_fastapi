from typing import TypedDict, Self, Any

from . import BaseFilter, BaseFilterValidator


class IntBtwFilterOpts(TypedDict, total=False):
    min_value: int
    max_value: int


class IntBtwFilterValidator(BaseFilterValidator[IntBtwFilterOpts], tuple[int | None, int | None]):
    min_value: int = None
    max_value: int = None

    @classmethod
    def validate(cls, v: str) -> Self:
        v1, v2 = None, None
        if '|' in v and v.count('|') == 1:
            v1, _, v2 = v.partition('|')
            v1, v2 = int(v1), int(v2)
        elif v.endswith('>'):
            v1 = int(v[:-1])
        elif v.startswith('<'):
            v2 = int(v[1:])
        else:
            raise ValueError('Некорректное значение. Нужно X|Y, X> или <Y')
        if cls.min_value is not None:
            if v1 is not None and v1 < cls.min_value:
                raise ValueError(f'X меньше минимального ({cls.min_value})')
            if v2 is not None and v2 < cls.min_value:
                raise ValueError(f'Y меньше минимального ({cls.min_value})')
        if cls.max_value is not None:
            if v1 is not None and v1 > cls.max_value:
                raise ValueError(f'X больше максимального ({cls.max_value})')
            if v2 is not None and v2 > cls.max_value:
                raise ValueError(f'Y больше максимального ({cls.max_value})')
        return cls((v1, v2))

    @classmethod
    def __schema__(cls) -> dict[str, Any]:
        return {
            'type': 'string',
            'minimum': cls.min_value,
            'maximum': cls.max_value,
        }


class BaseIntBtwFilter(BaseFilter[tuple[int | None, int | None], IntBtwFilterOpts, IntBtwFilterValidator]):
    suffix = '__btw'
    base_validator = IntBtwFilterValidator

    @classmethod
    def describe(cls):
        text = ''
        if cls.validator.min_value is not None:
            text += f'Минимум - {cls.validator.min_value}.\n'
        if cls.validator.max_value is not None:
            text += f'Максимум - {cls.validator.max_value}.\n'
        return text + 'Задаёт интервал (включая указанные значения).\n' \
                      'Возможные значения: X|Y - интервал от X до Y; X> - значения больше X, <Y - значения меньше Y'

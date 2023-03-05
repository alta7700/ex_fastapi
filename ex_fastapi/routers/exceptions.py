from typing import Iterable, Iterator, Self


class ItemNotFound(Exception):
    pass


class FieldsError(Exception):
    fields: list[str]
    key: str

    def __init__(self, *args, fields: Iterable[str] = None):
        super().__init__(*args)
        self.fields = list(fields or [])

    def with_prefix(self, prefix: str) -> None:
        self.fields = [f'{prefix}.{f}' for f in self.fields]


class NotUnique(FieldsError):
    key = 'notUnique'


class NotFoundFK(FieldsError):
    key = 'notFoundFK'


class MultipleFieldsError(Exception):
    errors: list[FieldsError]

    def __init__(self, *args, errors: Iterable[FieldsError] = None):
        super().__init__(*args)
        self.errors = errors or []

    def add_errors(self, *errors: FieldsError) -> Self:
        self.errors.extend(errors)
        return self

    def with_prefix(self, prefix: str) -> Self:
        for err in self.errors:
            if isinstance(err, FieldsError):
                err.with_prefix(prefix)
        return self

    def __iter__(self) -> Iterator[FieldsError]:
        return self.errors.__iter__()

    def __bool__(self) -> bool:
        return not not self.errors


class FieldErrors(Exception):
    errors: dict[str, str | dict[str, str]]

    def __init__(self, *args, errors: Iterable[FieldsError] = None):
        super().__init__(*args)
        self.errors = {}
        if errors:
            for error in errors:
                self.add_error(error)

    def add_error(self, e: FieldsError) -> None:
        key = e.key

        def add_error_in_place(d: dict[str, str | dict[str, str]], field_name: str):
            base_name, _, other_names = field_name.partition('.')
            if other_names:
                if base_name in d:
                    temp = d[base_name]
                else:
                    d[base_name] = temp = {}
                add_error_in_place(temp, other_names)
            else:
                d[base_name] = key

        for f_name in e.fields:
            add_error_in_place(self.errors, f_name)

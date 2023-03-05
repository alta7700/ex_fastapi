from typing import Optional, Any, Type, Callable

from fastapi import Depends, Query, Request
from pydantic import NonNegativeInt

from ex_fastapi import CommaSeparatedOf, snake_case
from ex_fastapi.routers.filters import BaseFilter

ROUTE = bool | dict[str, Any]
PAGINATION = tuple[Optional[int], Optional[int]]


def pagination_factory(max_limit: int | None) -> Any:
    """
    Created the pagination dependency to be used in the router
    """
    def pagination(
            skip: Optional[NonNegativeInt] = Query(None),
            limit: Optional[int] = Query(None, ge=1, le=max_limit)
    ) -> PAGINATION:
        return skip, limit

    return Depends(pagination)


def get_filters(filters: list[Type[BaseFilter]]):
    def wrapper(request: Request) -> list[BaseFilter]:
        qp = request.query_params
        return [final_f for f in filters if (final_f := f.from_qs(qp))]
    return wrapper


def sort_factory(available: set[str]) -> Callable[[...], set[str]]:
    def sort(fields: CommaSeparatedOf(str, wrapper=snake_case, in_query=True) = Query(
        None,
        alias='sort',
        description=f'Пиши,поля,через,запятую. Доступно: {", ".join(available)}'
    )) -> set[str]:
        result: set[str] = set()
        if fields:
            for field in fields:
                if field in available:
                    result.add(field)
        return result

    return sort

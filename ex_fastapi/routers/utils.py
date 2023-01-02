from typing import Optional, Any

from fastapi import Depends, Query
from pydantic import NonNegativeInt

ROUTE = bool | dict[str, Any]
PAGINATION = tuple[Optional[int], Optional[int]]


def pagination_factory(max_limit: int = 100) -> Any:
    """
    Created the pagination dependency to be used in the router
    """

    def pagination(
            skip: Optional[NonNegativeInt] = Query(None),
            limit: Optional[int] = Query(50, ge=1, le=max_limit)
    ) -> PAGINATION:
        return skip, limit

    return Depends(pagination)

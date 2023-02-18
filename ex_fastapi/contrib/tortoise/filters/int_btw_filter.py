from tortoise.queryset import QuerySet

from ex_fastapi.routers.filters import BaseIntBtwFilter


class IntBtwFilter(BaseIntBtwFilter):
    def filter(self, query: QuerySet) -> QuerySet:
        v1, v2 = self.value
        opts = {}
        if v1 is not None:
            opts[f'{self.field_name}__gte'] = v1
        if v2 is not None:
            opts[f'{self.field_name}__lte'] = v2
        if opts:
            query = query.filter(**opts)
        return query

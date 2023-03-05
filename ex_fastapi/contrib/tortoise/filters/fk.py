from tortoise.queryset import QuerySet
from ex_fastapi.routers.filters import BaseIntForeignKeyFilter


class IntForeignKeyFilter(BaseIntForeignKeyFilter):
    def filter(self, query: QuerySet) -> QuerySet:
        return query.filter(**{self.field_name: self.value})

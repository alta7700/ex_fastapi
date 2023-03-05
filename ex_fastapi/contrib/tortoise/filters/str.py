from tortoise.queryset import QuerySet

from ex_fastapi.routers.filters import BaseStrStartswithFilter, BaseStrIstartswithFilter


class StrStartswithFilter(BaseStrStartswithFilter):
    def filter(self, query: QuerySet) -> QuerySet:
        return query.filter(**{f'{self.field_name}__startswith': self.value})


class StrIstartswithFilter(BaseStrIstartswithFilter):
    def filter(self, query: QuerySet) -> QuerySet:
        return query.filter(**{f'{self.field_name}__istartswith': self.value})

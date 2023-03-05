from . import BaseIntFilter


class BaseIntForeignKeyFilter(BaseIntFilter):

    @classmethod
    def describe(cls):
        return f'Пиши в query {cls.camel_source}=id'

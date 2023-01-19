from typing import Self

from tortoise import fields

from . import BaseModel


class ContentType(BaseModel):
    id: int
    name: str = fields.CharField(max_length=50, unique=True)
    instances_by_id: dict[int, Self] = {}
    instances_by_name: dict[str, Self] = {}

    class Meta:
        table = "content_types"

    @classmethod
    def get_by_id(cls, _id: int) -> Self:
        return cls.instances_by_id[_id]

    @classmethod
    def get_by_name(cls, _name: str) -> Self:
        return cls.instances_by_name[_name]

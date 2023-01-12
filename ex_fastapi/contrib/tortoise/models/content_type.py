from tortoise import fields

from .. import Model

__all__ = ["ContentType"]


class ContentType(Model):
    id: int
    name: str = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "content_types"

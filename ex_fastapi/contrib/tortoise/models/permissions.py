from tortoise import fields

from .content_type import ContentType
from .. import Model


__all__ = ["Permission", "PermissionGroup", "PermissionMixin"]


class Permission(Model):
    id: int
    name: str = fields.CharField(max_length=50)
    content_type: fields.ForeignKeyRelation[ContentType] = fields.ForeignKeyField(
        'auth.ContentType', on_delete=fields.CASCADE, related_name='permissions'
    )

    class Meta:
        table = "permission"
        ordering = ("content_type", "name")
        unique_together = (('name', 'content_type'),)


class PermissionGroup(Model):
    id: int
    name: str = fields.CharField(max_length=100, description='Наименование', unique=True)
    permissions: fields.ManyToManyRelation["Permission"] = fields.ManyToManyField('models.Permission')

    class Meta:
        table = "permission_group"
        ordering = ('name',)

    def repr(self) -> str:
        """Должность"""
        return self.name


class PermissionMixin(Model):
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField('models.Permission')
    group: fields.ManyToManyRelation[PermissionGroup] = fields.ManyToManyField('models.PermissionGroup')

    class Meta:
        abstract = True

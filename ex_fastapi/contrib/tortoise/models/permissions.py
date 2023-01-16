from tortoise import fields

from .content_type import ContentType
from .. import Model


__all__ = ["Permission", "PermissionGroup", "PermissionMixin"]


class Permission(Model):
    id: int
    name: str = fields.CharField(max_length=50)
    content_type: fields.ForeignKeyRelation[ContentType] = fields.ForeignKeyField(
        'models.ContentType', on_delete=fields.CASCADE, related_name='permissions'
    )

    class Meta:
        table = "permissions"
        ordering = ("content_type__id", "name")
        unique_together = (('name', 'content_type'),)


class PermissionGroup(Model):
    id: int
    name: str = fields.CharField(max_length=100, description='Наименование', unique=True)
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField('models.Permission')

    class Meta:
        table = "permission_groups"
        ordering = ('name',)

    def repr(self) -> str:
        """Должность"""
        return self.name


class PermissionMixin(Model):
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField('models.Permission')
    groups: fields.ManyToManyRelation[PermissionGroup] = fields.ManyToManyField('models.PermissionGroup')

    class Meta:
        abstract = True

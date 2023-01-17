from tortoise import fields

from .content_type import ContentType
from .. import Model


__all__ = ["Permission", "PermissionGroup", "PermissionMixin"]


class Permission(Model):
    id: int
    name: str = fields.CharField(max_length=50)
    content_type: fields.ForeignKeyRelation[ContentType] | ContentType = fields.ForeignKeyField(
        'models.ContentType', on_delete=fields.CASCADE, related_name='permissions'
    )

    class Meta:
        table = "permissions"
        ordering = ("content_type__id", "name")
        unique_together = (('name', 'content_type'),)

    def __str__(self):
        return f'Can {self.name} {self.content_type.name}'


class PermissionGroup(Model):
    id: int
    name: str = fields.CharField(max_length=100, description='Наименование', unique=True)
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField(
        'models.Permission', related_name='groups'
    )

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

from tortoise import fields

from .content_type import ContentType
from . import BaseModel


class Permission(BaseModel):
    id: int
    name: str = fields.CharField(max_length=50)
    content_type_id: int
    content_type: fields.ForeignKeyRelation[ContentType] | ContentType = fields.ForeignKeyField(
        'models.ContentType', on_delete=fields.CASCADE, related_name='permissions'
    )

    class Meta:
        table = "permissions"
        ordering = ("content_type_id", "name")
        unique_together = (('name', 'content_type'),)

    def __str__(self):
        return f'Can {self.name} {self.content_type.name}'

    @property
    def content_type_name(self):
        return ContentType.get_by_id(self.content_type_id)


class PermissionGroup(BaseModel):
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


class PermissionMixin(BaseModel):
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField('models.Permission')
    groups: fields.ManyToManyRelation[PermissionGroup] = fields.ManyToManyField('models.PermissionGroup')

    class Meta:
        abstract = True

    @property
    def all_permissions(self) -> set[Permission]:
        return {*self.permissions, *(p for g in self.groups for p in g.permissions)}

    @classmethod
    def get_queryset_prefetch_related(cls, path: str, method: str) -> set[str]:
        pr = super().get_queryset_prefetch_related(path, method)
        pr.add('permissions')
        pr.add('groups__permissions')
        return pr

from tortoise import Tortoise, connections
from tortoise.log import logger


async def connect_db(config: dict = None):
    await Tortoise.init(config=config)
    logger.info(f'Tortoise-ORM started, {connections._get_storage()}, {Tortoise.apps}')


async def close_db_connection():
    await connections.close_all()
    logger.info("Tortoise-ORM shutdown")


def on_start(config: dict = None):
    async def wrapper():
        await connect_db(config)
        await check_permissions()

    return wrapper


on_shutdown = close_db_connection


async def check_permissions():
    from .models import ContentType, Permission
    from aerich.models import Aerich
    all_models = list(Tortoise.apps.get('models').values())
    if ContentType not in all_models:
        return
    old_names = [ct.name async for ct in ContentType.all()]
    new_names = []
    for model in all_models:
        if model is not Aerich and model is not ContentType:
            model_name = model.__name__
            if model_name in old_names:
                old_names.remove(model_name)
            else:
                new_names.append(model_name)
    if old_names:
        await ContentType.filter(name__in=old_names).delete()
    if new_names:
        await ContentType.bulk_create([ContentType(name=n) for n in new_names])
    content_types = await ContentType.all()
    permissions = await Permission.all()

    create_perms: list[Permission] = []
    delete_perm_ids: list[int] = []
    for ct in content_types:
        ContentType.instances_by_id[ct.id] = ct
        ContentType.instances_by_name[ct.name] = ct

        model = Tortoise.apps['models'][ct.name]
        need_perm_names: list[str] = ['get', 'create', 'edit', 'delete', *getattr(model, 'ADDITIONAL_PERMS', ())]
        for perm in filter(lambda p: p.content_type_id == ct.id, permissions):
            if perm.name in need_perm_names:
                need_perm_names.remove(perm.name)
            else:
                delete_perm_ids.append(perm.id)
        if need_perm_names:
            create_perms.extend(Permission(content_type=ct, name=perm_name) for perm_name in need_perm_names)
    if create_perms:
        await Permission.bulk_create(create_perms)
    if delete_perm_ids:
        await Permission.filter(id__in=delete_perm_ids)

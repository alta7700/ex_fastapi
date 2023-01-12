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
        await check_content_types()

    return wrapper


on_shutdown = close_db_connection


async def check_content_types():
    from .models import ContentType
    from aerich.models import Aerich
    all_models = list(Tortoise.apps.get('models').values())
    if ContentType in all_models:
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


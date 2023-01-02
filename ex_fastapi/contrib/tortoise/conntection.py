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

    return wrapper


on_shutdown = close_db_connection

try:
    import tortoise
except ImportError:
    print('Try pip install tortoise-orm[asyncpg]')


from .model import Model, default_of, max_len_of
from .crud_service import TortoiseCRUDService
from .conntection import on_start, on_shutdown

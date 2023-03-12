from typing import Literal

from fastapi import FastAPI

from .default_validators import \
    default_exception_handlers, \
    change_openapi_validation_error_schema


class ExFastAPI(FastAPI):
    def __init__(
            self,
            *,
            db_provider: Literal['tortoise'] = None,
            db_config: dict = None,
            **kwargs
    ) -> None:
        kwargs.setdefault('swagger_ui_parameters', {"operationsSorter": "method", "docExpansion": "none"})
        exception_handlers = kwargs.get('exception_handlers', {})
        kwargs['exception_handlers'] = {**default_exception_handlers, **exception_handlers}
        super().__init__(**kwargs)

        if db_config:
            match db_provider:
                case 'tortoise':
                    from .contrib import tortoise
                    db_on_start = tortoise.on_start(config=db_config)
                    db_on_shutdown = tortoise.on_shutdown
                case _:
                    raise Exception(f'Unknown {db_provider=}')
            if db_on_start:
                self.router.on_startup.append(db_on_start)
            if db_on_shutdown:
                self.router.on_shutdown.append(db_on_shutdown)

        async def default_on_start():
            try:
                change_openapi_validation_error_schema(self)
            except KeyError:
                pass

        self.router.on_startup.append(default_on_start)

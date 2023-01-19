import json
from typing import Any, Optional

from fastapi import HTTPException, BackgroundTasks
from starlette.responses import JSONResponse

from ex_fastapi.pydantic import CamelModel


class DefaultJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        for data_type, encoder in CamelModel.Config.json_encoders.items():
            if isinstance(o, data_type):
                return encoder(o)
        return super().default(o)


_default_encoder = DefaultJSONEncoder(
    ensure_ascii=False,
    allow_nan=False,
    indent=None,
    separators=(",", ":"),
)


class DefaultJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return _default_encoder.encode(content).encode("utf-8")


class BgHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[dict[str, Any]] = None,
        background: BackgroundTasks = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.background = background

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from .pydantic import CamelModel
from .default_response import DefaultJSONResponse, BgHTTPException


def add_HTTPException_handler(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> DefaultJSONResponse:
        headers = getattr(exc, "headers", None)
        if headers:
            return DefaultJSONResponse(exc.detail, status_code=exc.status_code, headers=headers)
        else:
            return DefaultJSONResponse(exc.detail, status_code=exc.status_code)

    @app.exception_handler(BgHTTPException)
    async def http_exception_handler(request: Request, exc: BgHTTPException) -> DefaultJSONResponse:
        headers = getattr(exc, "headers", None)
        if headers:
            response = DefaultJSONResponse(exc.detail, status_code=exc.status_code, headers=headers)
        else:
            response = DefaultJSONResponse(exc.detail, status_code=exc.status_code)
        response.background = exc.background
        return response


def add_validation_error_handler(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> DefaultJSONResponse:
        messages = {}
        for error in exc.errors():
            loc = error['loc']
            place = messages
            for item in loc[:-1]:
                if not (new_place := place.get(item)):
                    new_place = place[
                        item] = {}  # type: ignore # int and str are possible, but linter also see dict
                place = new_place
            place[loc[-1]] = error.get('msg')

        return DefaultJSONResponse(messages, status_code=422)


def change_openapi_validation_error_schema(app: FastAPI):
    obj = dict[str, dict[str, dict[str, str] | str] | str]

    class ValidationErr(CamelModel):
        body: Optional[obj]
        query: Optional[obj]
        file: Optional[obj]
        form: Optional[obj]
        path: Optional[obj]

    del app.openapi()['components']['schemas']['ValidationError']
    app.openapi()['components']['schemas']['HTTPValidationError']['properties'] = ValidationErr.schema()['properties']

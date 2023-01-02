from typing import Type

from fastapi import APIRouter, Response

from ex_fastapi import CamelModel
from ex_fastapi.auth.auth_errors import AuthErrors


def get_default_preset(
        token_user: Type[CamelModel],
        user_me_read: Type[CamelModel],

        **kwargs
):
    kwargs.setdefault('prefix', '/auth')
    kwargs.setdefault('tags', ['/auth'])
    router = APIRouter(**kwargs)

    @router.post('/login', response_model=user_me_read, responses=AuthErrors.responses(
        AuthErrors.not_authenticated,
    ))
    async def login(
            response: Response,
            user_service: UserService = Depends(get_sign_in_user),
    ):
        user_service.login(response)
        return user_service.read_me()

    @router.get('/logout', responses=Codes.responses(Codes.OK))
    async def logout(response: Response):
        delete_auth_cookie(response)
        return Codes.OK.resp

    @router.get('/check', response_model=UserMeRead, responses=Codes.responses(*AuthErrors.all_errors()))
    async def get_me(
            response: Response,
            user_service: UserService = Depends(get_auth())
    ):
        user_service.login(response)
        return user_service.read_model()


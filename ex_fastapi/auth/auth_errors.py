from ex_fastapi import BaseCodes


class AuthErrors(BaseCodes):
    invalid_token = 401, "Неверный авторизационный токен"
    expired_token = 401, "Истёк срок авторизации"
    not_authenticated = 401, "Не авторизован"
    permission_denied = 403, "Недостаточно прав"

    @classmethod
    def all_errors(cls) -> tuple:
        return cls.invalid_token, cls.expired_token, cls.not_authenticated

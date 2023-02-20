from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from ex_fastapi.global_objects import get_settings
from ex_fastapi.settings import MailingConfig


EMAIL_CONF: MailingConfig = get_settings('EMAIL_CONF')


class MailSender:

    fast_mail: FastMail

    def __init__(self, conf: MailingConfig):
        self.fast_mail = FastMail(conf)

    async def activation_email(
            self,
            to: EmailStr,
            username: str,
            uuid: UUID,
            temp_code: str,
            duration: timedelta,
            template: str = 'activation.html',
            subject: str = 'Account activation'):
        await self.send(to=to, template=template, subject=subject, data={
            'username': username,
            'uuid': uuid,
            'temp_code': temp_code,
            'duration': duration
        })

    async def send(self, to: EmailStr, data: dict[str, Any], template: str, subject: str):
        email_msg = MessageSchema(
            subject=subject,
            recipients=[to],
            template_body=data,
            subtype=MessageType.html
        )
        await self.fast_mail.send_message(email_msg, template_name=template)


default_mail_sender = MailSender(EMAIL_CONF)

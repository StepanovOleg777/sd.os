from email.message import EmailMessage
from email.utils import formataddr
from html import escape

import aiosmtplib

from backend.app.core.config import settings


class EmailServiceError(Exception):
    pass


class EmailService:
    async def send_email(
        self,
        to_email: str,
        subject: str,
        text: str,
        html: str | None = None,
    ) -> None:
        if not settings.SMTP_HOST:
            raise EmailServiceError(
                "SMTP_HOST не настроен."
            )

        if not settings.SMTP_USERNAME:
            raise EmailServiceError(
                "SMTP_USERNAME не настроен."
            )

        if not settings.SMTP_PASSWORD:
            raise EmailServiceError(
                "SMTP_PASSWORD не настроен."
            )

        if not settings.SMTP_FROM_EMAIL:
            raise EmailServiceError(
                "SMTP_FROM_EMAIL не настроен."
            )

        message = EmailMessage()

        message["From"] = formataddr(
            (
                settings.SMTP_FROM_NAME,
                settings.SMTP_FROM_EMAIL,
            )
        )

        message["To"] = to_email
        message["Subject"] = subject

        message.set_content(
            text
        )

        if html:
            message.add_alternative(
                html,
                subtype="html",
            )

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_SSL,
                timeout=15,
            )

        except Exception as exc:
            raise EmailServiceError(
                "Не удалось отправить письмо."
            ) from exc

    async def send_invitation(
        self,
        to_email: str,
        fio: str,
        invite_url: str,
    ) -> None:
        safe_fio = escape(
            fio
        )

        safe_url = escape(
            invite_url,
            quote=True,
        )

        subject = (
            "Приглашение в SD.OS"
        )

        text = (
            f"{fio}, здравствуйте.\n\n"
            "Для вас создана учётная запись SD.OS.\n\n"
            "Чтобы активировать её, перейдите по ссылке:\n"
            f"{invite_url}\n\n"
            "Ссылка действует 24 часа.\n\n"
            "Если вы не ожидали это письмо, "
            "просто проигнорируйте его."
        )

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<body style="
    margin:0;
    padding:0;
    background:#f4f5f7;
    font-family:Arial,sans-serif;
    color:#202124;
">
    <div style="
        max-width:560px;
        margin:40px auto;
        padding:32px;
        background:#ffffff;
        border-radius:12px;
    ">
        <h2 style="
            margin-top:0;
            margin-bottom:20px;
        ">
            SD.OS
        </h2>

        <p>
            {safe_fio}, здравствуйте.
        </p>

        <p>
            Для вас создана учётная запись SD.OS.
        </p>

        <p>
            Для активации учётной записи
            нажмите кнопку ниже.
        </p>

        <p style="
            margin:28px 0;
        ">
            <a
                href="{safe_url}"
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#6267ea;
                    color:#ffffff;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:600;
                "
            >
                Активировать учётную запись
            </a>
        </p>

        <p style="
            color:#6b6f76;
            font-size:13px;
        ">
            Ссылка действует 24 часа.
        </p>

        <p style="
            color:#6b6f76;
            font-size:13px;
        ">
            Если вы не ожидали это письмо,
            просто проигнорируйте его.
        </p>
    </div>
</body>
</html>
"""

        await self.send_email(
            to_email=to_email,
            subject=subject,
            text=text,
            html=html,
        )

    async def send_password_reset(
        self,
        to_email: str,
        fio: str,
        reset_url: str,
    ) -> None:
        safe_fio = escape(
            fio
        )

        safe_url = escape(
            reset_url,
            quote=True,
        )

        ttl = (
            settings.PASSWORD_RESET_TTL_MINUTES
        )

        subject = (
            "Восстановление пароля SD.OS"
        )

        text = (
            f"{fio}, здравствуйте.\n\n"
            "Был запрошен сброс пароля "
            "для вашей учётной записи SD.OS.\n\n"
            "Чтобы установить новый пароль, "
            "перейдите по ссылке:\n"
            f"{reset_url}\n\n"
            f"Ссылка действует {ttl} минут.\n\n"
            "Если вы не запрашивали восстановление "
            "пароля, ничего делать не нужно. "
            "Текущий пароль продолжает работать."
        )

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<body style="
    margin:0;
    padding:0;
    background:#f4f5f7;
    font-family:Arial,sans-serif;
    color:#202124;
">
    <div style="
        max-width:560px;
        margin:40px auto;
        padding:32px;
        background:#ffffff;
        border-radius:12px;
    ">
        <h2 style="
            margin-top:0;
            margin-bottom:20px;
        ">
            SD.OS
        </h2>

        <p>
            {safe_fio}, здравствуйте.
        </p>

        <p>
            Был запрошен сброс пароля
            для вашей учётной записи SD.OS.
        </p>

        <p>
            Чтобы установить новый пароль,
            нажмите кнопку ниже.
        </p>

        <p style="
            margin:28px 0;
        ">
            <a
                href="{safe_url}"
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#6267ea;
                    color:#ffffff;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:600;
                "
            >
                Установить новый пароль
            </a>
        </p>

        <p style="
            color:#6b6f76;
            font-size:13px;
        ">
            Ссылка действует {ttl} минут.
        </p>

        <p style="
            color:#6b6f76;
            font-size:13px;
        ">
            Если вы не запрашивали восстановление,
            просто проигнорируйте это письмо.
            Ваш текущий пароль не изменён.
        </p>
    </div>
</body>
</html>
"""

        await self.send_email(
            to_email=to_email,
            subject=subject,
            text=text,
            html=html,
        )


email_service = EmailService()
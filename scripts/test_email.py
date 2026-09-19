import asyncio

from backend.app.services.email_service import (
    EmailServiceError,
    email_service,
)

'''Отправка проверочного сообщения mail для проверки работоспособности SMTP'''

async def main() -> None:
    recipient = input(
        "Email получателя: "
    ).strip()

    try:
        await email_service.send_email(
            to_email=recipient,
            subject="Проверка SD.OS",
            text=(
                "Это тестовое письмо от SD.OS.\n\n"
                "SMTP-соединение работает."
            ),
            html="""
                <h2>SD.OS</h2>
                <p>
                    Это тестовое письмо от SD.OS.
                </p>
                <p>
                    SMTP-соединение работает.
                </p>
            """,
        )

    except EmailServiceError as exc:
        print(
            f"Ошибка: {exc}"
        )
        return

    print(
        "Письмо успешно отправлено."
    )


if __name__ == "__main__":
    asyncio.run(main())
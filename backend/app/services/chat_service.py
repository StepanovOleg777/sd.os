class ChatService:
    async def process_message(self, message: str) -> str:
        """
        Точка входа в обработку пользовательского сообщения.

        Позже здесь будет вызов Supervisor,
        который определит необходимого агента
        и соберёт финальный ответ руководителю.
        """

        return (
            "Интерфейс SD.OS работает. "
            "Главный ИИ пока не подключён."
        )


chat_service = ChatService()
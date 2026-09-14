import json
from typing import Any

from openai import AsyncOpenAI

from backend.app.core.config import settings
from backend.app.services.contact_agent import contact_agent
from backend.app.services.sim_card_tracker_client import (
    SimCardTrackerError,
    sim_card_tracker_client,
)


SYSTEM_PROMPT = """
Ты — главный ИИ интерфейса SD.OS.

Сейчас тебе доступен корпоративный справочник сотрудников.

Ты можешь свободно отвечать на вопросы пользователя и использовать
инструменты справочника, когда вопрос касается сотрудников компании.

Данные справочника являются источником фактов.
Не придумывай ФИО, телефоны, email, должности, отделы, объекты,
руководителей, статусы и примечания.

Если пользователь спрашивает о сотрудниках, используй инструменты,
а не отвечай по памяти.

Пользователь сейчас работает с максимальными правами руководителя.
Ограничения по ролям пока не применяются.

search_directory используй для вопросов о сотрудниках:
ФИО, руководитель, отдел, должность, объект, статус, контакты,
телефоны, email, примечания и списки сотрудников.

prepare_call используй, когда пользователь хочет позвонить сотруднику.

prepare_email используй, когда пользователь хочет написать сотруднику.

Отвечай на русском языке, естественно и кратко.
"""


TOOLS = [
    {
        "type": "function",
        "name": "search_directory",
        "description": (
            "Поиск сотрудников корпоративного справочника. "
            "Используется для получения информации о сотрудниках, "
            "их должностях, отделах, объектах, руководителях, "
            "статусах, телефонах, email и примечаниях."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ФИО или часть ФИО сотрудника.",
                },
                "department": {
                    "type": "string",
                    "description": "Отдел.",
                },
                "position": {
                    "type": "string",
                    "description": "Должность.",
                },
                "location": {
                    "type": "string",
                    "description": "Объект или место работы.",
                },
                "supervisor": {
                    "type": "string",
                    "description": "ФИО или часть ФИО руководителя.",
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "working",
                        "dismissed",
                    ],
                    "description": "Статус сотрудника.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "prepare_call",
        "description": (
            "Подготовить звонок сотруднику компании."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ФИО или часть ФИО сотрудника.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "prepare_email",
        "description": (
            "Подготовить письмо сотруднику на корпоративную почту."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ФИО или часть ФИО сотрудника.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]


class OpenAIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

        # Временная память текущего диалога.
        # Позже перенесём состояние в PostgreSQL.
        self.previous_response_id: str | None = None

    async def process(
        self,
        message: str,
    ) -> tuple[str, dict[str, Any] | None]:
        if not settings.OPENAI_API_KEY:
            return (
                "OPENAI_API_KEY не настроен.",
                None,
            )

        request_kwargs = {
            "model": settings.OPENAI_MODEL,
            "instructions": SYSTEM_PROMPT,
            "input": message,
            "tools": TOOLS,
        }

        if self.previous_response_id:
            request_kwargs["previous_response_id"] = (
                self.previous_response_id
            )

        response = await self.client.responses.create(
            **request_kwargs
        )

        action = None

        while True:
            function_calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            if not function_calls:
                # Запоминаем последний ответ OpenAI,
                # чтобы следующее сообщение продолжило диалог.
                self.previous_response_id = response.id

                return (
                    response.output_text,
                    action,
                )

            tool_outputs = []

            for call in function_calls:
                try:
                    arguments = json.loads(
                        call.arguments
                    )
                except json.JSONDecodeError:
                    arguments = {}

                result, new_action = await self._execute_tool(
                    call.name,
                    arguments,
                )

                if new_action is not None:
                    action = new_action

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )

            response = await self.client.responses.create(
                model=settings.OPENAI_MODEL,
                instructions=SYSTEM_PROMPT,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
            )

    async def _execute_tool(
        self,
        name: str,
        arguments: dict,
    ) -> tuple[Any, dict[str, Any] | None]:

        if name == "search_directory":
            try:
                contacts = (
                    await sim_card_tracker_client.search_contacts(
                        query=arguments.get("query", ""),
                        department=arguments.get("department", ""),
                        position=arguments.get("position", ""),
                        location=arguments.get("location", ""),
                        supervisor=arguments.get("supervisor", ""),
                        status=arguments.get("status", ""),
                    )
                )

                return (
                    {
                        "count": len(contacts),
                        "results": contacts,
                    },
                    None,
                )

            except SimCardTrackerError as exc:
                return (
                    {
                        "error": str(exc),
                    },
                    None,
                )

        if name == "prepare_call":
            result = await contact_agent.prepare_call(
                arguments.get(
                    "query",
                    "",
                )
            )

            return (
                {
                    "status": result.status,
                    "answer": result.answer,
                },
                result.action,
            )

        if name == "prepare_email":
            result = await contact_agent.prepare_email(
                arguments.get(
                    "query",
                    "",
                )
            )

            return (
                {
                    "status": result.status,
                    "answer": result.answer,
                },
                result.action,
            )

        return (
            {
                "error": f"Неизвестный инструмент: {name}",
            },
            None,
        )


openai_service = OpenAIService()
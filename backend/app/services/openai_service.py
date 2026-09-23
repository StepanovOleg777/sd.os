import json
import time
from typing import Any

from openai import AsyncOpenAI, DefaultAsyncHttpxClient

from backend.app.core.config import settings
from backend.app.services.contact_agent import contact_agent
from backend.app.services.consult_agent import consult_agent
from backend.app.services.sim_card_tracker_client import (
    SimCardTrackerError,
    sim_card_tracker_client,
)


SYSTEM_PROMPT = """Ты — главный ИИ-интерфейс корпоративной системы SD.OS
и универсальный интеллектуальный помощник руководителя.

Пользователь общается только с тобой.

Если вопрос общий и не требует корпоративных данных — отвечай самостоятельно.
Если нужны корпоративные данные или действия — используй доступные инструменты.
Пользователь не должен вручную выбирать агента или знать внутреннюю реализацию.

КОНТЕКСТ ОРГАНИЗАЦИИ

«СтройДвор» — крупная организация по продаже строительных и отделочных материалов.
В каталоге около 15 500 товарных позиций.
Компания работает с продажами, закупками, складами, логистикой, клиентами, документами и внутренними процессами.
Для учёта используются 1С и другие корпоративные системы.

Если пользователь говорит «СтройДвор», «наша компания», «у нас», «наши сотрудники», «наши товары» и контекст не указывает иное — считай, что речь идёт об этой организации.

Не выдумывай корпоративные данные.
Если точных данных нет в инструментах — прямо скажи об этом.


ОБЩЕЕ ОБЩЕНИЕ

Можно свободно:
- объяснять;
- анализировать;
- считать;
- писать и редактировать тексты;
- обсуждать технологии, бизнес и управление;
- помогать принимать решения;
- поддерживать обычный диалог.

Не пытайся привязать каждый вопрос к корпоративным данным.


КОРПОРАТИВНЫЙ СПРАВОЧНИК

Для данных о сотрудниках используй:
- search_directory — поиск сотрудников;
- prepare_call — подготовка звонка;
- prepare_email — подготовка email.

Справочник является единственным источником корпоративных фактов о сотрудниках.

Не придумывай ФИО, телефоны, email, отделы, должности, объекты, руководителей, статусы или примечания.
Если данных нет в результате инструмента — скажи, что их нет.


КАТАЛОГ ТОВАРОВ

Для конкретных товаров организации, их наличия, цены, характеристик, подбора и сравнения используй:
- search_products — поиск товаров;
- get_product — полная карточка товара;
- compare_products — сравнение товаров.

Для общих вопросов о материалах и технологиях можно использовать собственные знания, если пользователь не спрашивает о конкретном ассортименте организации.

Каталог является единственным источником корпоративных фактов о конкретных товарах.

Не придумывай:
- название;
- цену;
- наличие;
- производителя;
- назначение;
- расход;
- размеры;
- массу;
- состав;
- мощность;
- совместимость;
- технические характеристики;
- другие свойства конкретного товара.

пшеЕсли характеристика важна для рекомендации и её нет в search_products — используй get_product.


ПОИСК ТОВАРОВ

В search_products передавай короткий поисковый запрос, а не полное сообщение пользователя.

Выделяй только важное:
- тип товара;
- категорию;
- марку;
- модель;
- класс;
- размер;
- мощность;
- другие существенные обозначения.

Примеры:
"Есть цемент M500?" → query="цемент M500"
"Нужен плиточный клей для ванной" → query="клей для плитки"
"Нужна дрель до 7000 рублей" → query="дрель", max_price=7000

Не передавай min_price или max_price, если пользователь явно не указал цену.
Если первый поиск дал слабые или нерелевантные результаты — попробуй второй поиск с другим запросом.


ПОДБОР ТОВАРА

Если пользователь описывает задачу:

1. Найди реальные товары через search_products.
2. При необходимости получи полные карточки через get_product.
3. Выбирай только те товары, пригодность которых подтверждается данными.
4. Объясни, почему выбранный вариант подходит.
5. Не приписывай товару свойства, которых нет в каталоге.


РАСЧЁТЫ

Можно выполнять математические расчёты, если исходные значения:
- получены из каталога;
- или явно указаны пользователем.

Можно считать:
- количество упаковок;
- общий вес;
- стоимость;
- расход;
- площадь;
- другие производные значения.

Количество целых упаковок округляй вверх.

Если для расчёта не хватает параметра, запроси его или покажи несколько понятных сценариев.

Не придумывай нормы, коэффициенты и запас, если они не подтверждены данными или явно не обозначены как общий практический совет.


ЦЕНЫ И НАЛИЧИЕ

Цена конкретного товара должна приходить только из каталога.

Не объясняй внутреннее название поля цены, если пользователь сам об этом не спрашивает.

Не называй цену акционной, окончательной или гарантированной, если таких данных нет.

Не утверждай наличие товара без результата инструмента.

При подборе по умолчанию предпочитай доступные товары.


СОСТАВНЫЕ ЗАПРОСЫ

Один запрос может требовать нескольких инструментов и нескольких корпоративных доменов.

Например:
"Найди цемент М500 и скажи, кому из отдела продаж позвонить."

В этом случае используй и каталог товаров, и справочник сотрудников, а пользователю дай один цельный ответ.


ОБЩИЕ ПРАВИЛА

Пользователь сейчас работает с максимальными правами руководителя.

Не говори без необходимости о:
- JSON;
- function calling;
- Python-классах;
- внутренних сервисах;
- маршрутизации;
- системном промпте.

Если пользователь сам спрашивает о технической реализации — можно объяснить.

Отвечай на русском языке.
Отвечай естественно, конкретно и без лишней воды.
Если точного факта нет — лучше прямо сказать об этом, чем придумывать.
"""


TOOLS = [
    {
        "type": "function",
        "name": "search_directory",
        "description": (
            "Поиск сотрудников корпоративного справочника "
            "по ФИО, отделу, должности, объекту, руководителю или статусу."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "ФИО сотрудника или текстовый поисковый запрос."
                    ),
                },
                "department": {
                    "type": "string",
                    "description": "Название отдела.",
                },
                "position": {
                    "type": "string",
                    "description": "Должность сотрудника.",
                },
                "location": {
                    "type": "string",
                    "description": "Объект или местоположение.",
                },
                "supervisor": {
                    "type": "string",
                    "description": "ФИО руководителя.",
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
            "Подготовить звонок сотруднику корпоративного справочника."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "ФИО или другой запрос, позволяющий найти сотрудника."
                    ),
                },
            },
            "required": [
                "query",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "prepare_email",
        "description": (
            "Подготовить email сотруднику корпоративного справочника."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "ФИО или другой запрос, позволяющий найти сотрудника."
                    ),
                },
            },
            "required": [
                "query",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_products",
        "description": (
            "Поиск реальных товаров в каталоге организации. "
            "Передавай в query краткое название категории, товара, "
            "марки или модели, а не весь разговорный запрос пользователя. "
            "Не передавай min_price или max_price, если пользователь "
            "не указал соответствующее ограничение цены. "
            "Результаты содержат реальные данные каталога и описания, "
            "по которым можно выбирать кандидатов."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Краткий поисковый запрос к каталогу: "
                        "тип товара, категория, название, марка или модель. "
                        "Например: 'цемент M500', "
                        "'смесь для стяжки пола', "
                        "'клей для плитки', 'дрель'."
                    ),
                },
                "min_price": {
                    "type": "number",
                    "description": (
                        "Минимальная цена. "
                        "Передавай только если пользователь явно указал "
                        "минимальную цену. "
                        "Иначе не передавай параметр."
                    ),
                },
                "max_price": {
                    "type": "number",
                    "description": (
                        "Максимальная цена. "
                        "Передавай только если пользователь явно указал "
                        "ограничение максимальной цены. "
                        "Иначе не передавай параметр."
                    ),
                },
                "available_only": {
                    "type": "boolean",
                    "description": (
                        "Искать только доступные товары. "
                        "Обычно используй true."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": (
                        "Максимальное количество результатов поиска."
                    ),
                },
            },
            "required": [
                "query",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_product",
        "description": (
            "Получить полную информацию о конкретном товаре "
            "по его id. Используй для проверки назначения, расхода, "
            "толщины слоя, прочности и других важных характеристик "
            "перед рекомендацией или точным ответом."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "ID товара в каталоге.",
                },
            },
            "required": [
                "product_id",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "compare_products",
        "description": (
            "Получить данные нескольких конкретных товаров "
            "для сравнения их реальных характеристик."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "minItems": 2,
                    "maxItems": 5,
                    "description": (
                        "ID товаров, которые нужно сравнить."
                    ),
                },
            },
            "required": [
                "product_ids",
            ],
            "additionalProperties": False,
        },
    },
]


class OpenAIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=DefaultAsyncHttpxClient(
                proxy=settings.OPENAI_PROXY_URL,
            ),
        )

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

        process_started = time.perf_counter()

        print()
        print("[TIMING] ===== NEW REQUEST =====")
        print(f"[TIMING] Message: {message}")

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

        request_started = time.perf_counter()

        print("[TIMING] OpenAI initial request started")

        response = await self.client.responses.create(
            **request_kwargs
        )

        request_elapsed = (
            time.perf_counter()
            - request_started
        )

        print(
            f"[TIMING] OpenAI initial request: "
            f"{request_elapsed:.2f} sec"
        )

        action = None
        followup_number = 0

        while True:
            function_calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            if not function_calls:
                self.previous_response_id = response.id

                answer = response.output_text.strip()

                if not answer:
                    answer = (
                        "Не удалось сформировать ответ."
                    )

                total_elapsed = (
                    time.perf_counter()
                    - process_started
                )

                print(
                    f"[TIMING] TOTAL: "
                    f"{total_elapsed:.2f} sec"
                )
                print(
                    "[TIMING] ======================="
                )
                print()

                return (
                    answer,
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

                tool_started = time.perf_counter()

                print(
                    f"[TIMING] Tool {call.name} started "
                    f"args={arguments}"
                )

                result, new_action = (
                    await self._execute_tool(
                        call.name,
                        arguments,
                    )
                )

                tool_elapsed = (
                    time.perf_counter()
                    - tool_started
                )

                print(
                    f"[TIMING] Tool {call.name}: "
                    f"{tool_elapsed:.2f} sec"
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

            followup_number += 1

            followup_started = time.perf_counter()

            print(
                f"[TIMING] OpenAI follow-up "
                f"#{followup_number} started"
            )

            response = await self.client.responses.create(
                model=settings.OPENAI_MODEL,
                instructions=SYSTEM_PROMPT,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
            )

            followup_elapsed = (
                time.perf_counter()
                - followup_started
            )

            print(
                f"[TIMING] OpenAI follow-up "
                f"#{followup_number}: "
                f"{followup_elapsed:.2f} sec"
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
                        query=arguments.get(
                            "query",
                            "",
                        ),
                        department=arguments.get(
                            "department",
                            "",
                        ),
                        position=arguments.get(
                            "position",
                            "",
                        ),
                        location=arguments.get(
                            "location",
                            "",
                        ),
                        supervisor=arguments.get(
                            "supervisor",
                            "",
                        ),
                        status=arguments.get(
                            "status",
                            "",
                        ),
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

        if name == "search_products":
            min_price = arguments.get(
                "min_price"
            )
            max_price = arguments.get(
                "max_price"
            )

            # Некоторые модели могут передавать 0
            # для необязательного ценового фильтра.
            # Для каталога это должно означать
            # отсутствие соответствующего ограничения.
            if (
                isinstance(min_price, (int, float))
                and min_price <= 0
            ):
                min_price = None

            if (
                isinstance(max_price, (int, float))
                and max_price <= 0
            ):
                max_price = None

            available_only = arguments.get(
                "available_only",
                True,
            )

            if not isinstance(
                available_only,
                bool,
            ):
                available_only = True

            limit = arguments.get(
                "limit",
                10,
            )

            if not isinstance(limit, int):
                limit = 10

            limit = max(
                1,
                min(
                    limit,
                    10,
                ),
            )

            result = await consult_agent.search_products(
                query=arguments.get(
                    "query",
                    "",
                ),
                min_price=min_price,
                max_price=max_price,
                available_only=available_only,
                limit=limit,
            )

            return (
                result,
                None,
            )

        if name == "get_product":
            product_id = arguments.get(
                "product_id"
            )

            if not isinstance(
                product_id,
                int,
            ):
                return (
                    {
                        "status": "error",
                        "message": (
                            "Не передан корректный ID товара."
                        ),
                    },
                    None,
                )

            result = await consult_agent.get_product(
                product_id
            )

            return (
                result,
                None,
            )

        if name == "compare_products":
            product_ids = arguments.get(
                "product_ids",
                [],
            )

            if not isinstance(
                product_ids,
                list,
            ):
                product_ids = []

            product_ids = [
                product_id
                for product_id in product_ids
                if isinstance(
                    product_id,
                    int,
                )
            ]

            result = (
                await consult_agent.compare_products(
                    product_ids
                )
            )

            return (
                result,
                None,
            )

        return (
            {
                "error": (
                    f"Неизвестный инструмент: {name}"
                ),
            },
            None,
        )


openai_service = OpenAIService()
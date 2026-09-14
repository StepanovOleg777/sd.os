import re
from dataclasses import dataclass
from typing import Any

from backend.app.services.sim_card_tracker_client import (
    SimCardTrackerClient,
    SimCardTrackerError,
    sim_card_tracker_client,
)


@dataclass
class ContactAgentResult:
    status: str
    answer: str
    action: dict[str, Any] | None = None


class ContactAgent:
    def __init__(
        self,
        client: SimCardTrackerClient,
    ) -> None:
        self.client = client

    async def search(
        self,
        employee_query: str,
    ) -> list[dict]:
        query = self._clean_query(
            employee_query
        )

        contacts = await self.client.search_contacts(
            query
        )

        if contacts:
            return contacts

        normalized_query = (
            self._normalize_person_query(
                query
            )
        )

        if normalized_query == query:
            return []

        return await self.client.search_contacts(
            normalized_query
        )

    async def prepare_call(
        self,
        employee_query: str,
    ) -> ContactAgentResult:
        try:
            contacts = await self.search(
                employee_query
            )

        except SimCardTrackerError as exc:
            return ContactAgentResult(
                status="error",
                answer=(
                    "Не удалось получить контакты "
                    f"из sim_card_tracker: {exc}"
                ),
            )

        if not contacts:
            return ContactAgentResult(
                status="not_found",
                answer=(
                    "Не удалось найти сотрудника "
                    f"«{employee_query.strip()}»."
                ),
            )

        if len(contacts) > 1:
            return self._build_person_choice(
                contacts=contacts,
                intent="call",
            )

        return self._build_call_result(
            contacts[0]
        )

    async def prepare_email(
        self,
        employee_query: str,
    ) -> ContactAgentResult:
        try:
            contacts = await self.search(
                employee_query
            )

        except SimCardTrackerError as exc:
            return ContactAgentResult(
                status="error",
                answer=(
                    "Не удалось получить контакты "
                    f"из sim_card_tracker: {exc}"
                ),
            )

        if not contacts:
            return ContactAgentResult(
                status="not_found",
                answer=(
                    "Не удалось найти сотрудника "
                    f"«{employee_query.strip()}»."
                ),
            )

        if len(contacts) > 1:
            return self._build_person_choice(
                contacts=contacts,
                intent="email",
            )

        return self._build_email_result(
            contacts[0]
        )

    def _build_person_choice(
        self,
        contacts: list[dict],
        intent: str,
    ) -> ContactAgentResult:
        choices = []

        for employee in contacts:
            fio = employee.get(
                "fio",
                "",
            )

            if not fio:
                continue

            details = []

            position = employee.get(
                "position",
                "",
            )

            department = employee.get(
                "department",
                "",
            )

            if position:
                details.append(
                    position
                )

            if department:
                details.append(
                    department
                )

            label = fio

            if details:
                label += (
                    " — "
                    + ", ".join(details)
                )

            choices.append(
                {
                    "label": label,
                    "value": fio,
                }
            )

        if intent == "email":
            answer = (
                "Нашёл несколько сотрудников. "
                "Уточните, кому нужно написать."
            )

        else:
            answer = (
                "Нашёл несколько сотрудников. "
                "Уточните, кому нужно позвонить."
            )

        return ContactAgentResult(
            status="choose_person",
            answer=answer,
            action={
                "type": "choose_person",
                "intent": intent,
                "choices": choices,
            },
        )

    def _build_call_result(
        self,
        employee: dict,
    ) -> ContactAgentResult:
        fio = employee.get(
            "fio",
            "Сотрудник",
        )

        phones = employee.get(
            "phones",
            {},
        )

        corporate_phones = phones.get(
            "corporate",
            [],
        )

        personal_phones = phones.get(
            "personal",
            [],
        )

        active_corporate = []

        for phone in corporate_phones:
            number = phone.get(
                "number",
                "",
            )

            status = phone.get(
                "status",
                "",
            )

            if (
                status == "active"
                and number
            ):
                active_corporate.append(
                    number
                )

        active_corporate = (
            self._unique_numbers(
                active_corporate
            )
        )

        personal_phones = (
            self._unique_numbers(
                personal_phones
            )
        )

        if len(active_corporate) == 1:
            return self._ready_call(
                fio=fio,
                number=active_corporate[0],
                phone_type="corporate",
            )

        if len(active_corporate) > 1:
            return self._build_phone_choice(
                fio=fio,
                numbers=active_corporate,
                phone_type="corporate",
            )

        if len(personal_phones) == 1:
            return self._ready_call(
                fio=fio,
                number=personal_phones[0],
                phone_type="personal",
            )

        if len(personal_phones) > 1:
            return self._build_phone_choice(
                fio=fio,
                numbers=personal_phones,
                phone_type="personal",
            )

        return ContactAgentResult(
            status="no_phone",
            answer=(
                f"Нашёл {fio}, но доступного "
                "номера телефона нет."
            ),
        )

    def _build_email_result(
        self,
        employee: dict,
    ) -> ContactAgentResult:
        fio = employee.get(
            "fio",
            "Сотрудник",
        )

        email = str(
            employee.get(
                "corporate_email",
                "",
            )
            or ""
        ).strip()

        if not email:
            return ContactAgentResult(
                status="no_email",
                answer=(
                    f"Нашёл {fio}, но корпоративная "
                    "почта не указана."
                ),
            )

        return ContactAgentResult(
            status="ready",
            answer=(
                f"Нашёл {fio}. "
                f"Корпоративная почта: {email}."
            ),
            action={
                "type": "email",
                "label": "Написать письмо",
                "value": email,
                "href": f"mailto:{email}",
            },
        )

    def _ready_call(
        self,
        fio: str,
        number: str,
        phone_type: str,
    ) -> ContactAgentResult:
        type_text = (
            "корпоративный"
            if phone_type == "corporate"
            else "личный"
        )

        return ContactAgentResult(
            status="ready",
            answer=(
                f"Нашёл {fio}. "
                f"Использую {type_text} номер "
                f"{number}."
            ),
            action={
                "type": "call",
                "label": "Позвонить",
                "value": number,
                "href": self._make_tel_href(
                    number
                ),
            },
        )

    def _build_phone_choice(
        self,
        fio: str,
        numbers: list[str],
        phone_type: str,
    ) -> ContactAgentResult:
        type_text = (
            "корпоративных"
            if phone_type == "corporate"
            else "личных"
        )

        choices = []

        for number in numbers:
            choices.append(
                {
                    "label": number,
                    "value": number,
                    "href": self._make_tel_href(
                        number
                    ),
                }
            )

        return ContactAgentResult(
            status="choose_phone",
            answer=(
                f"У {fio} несколько "
                f"{type_text} номеров. "
                "Выберите нужный."
            ),
            action={
                "type": "choose_phone",
                "intent": "call",
                "choices": choices,
            },
        )

    @staticmethod
    def _unique_numbers(
        numbers: list[str],
    ) -> list[str]:
        result = []
        seen = set()

        for number in numbers:
            clean = str(
                number
            ).strip()

            if (
                not clean
                or clean in seen
            ):
                continue

            seen.add(
                clean
            )

            result.append(
                clean
            )

        return result

    @staticmethod
    def _make_tel_href(
        number: str,
    ) -> str:
        normalized = re.sub(
            r"[^\d+]",
            "",
            number,
        )

        return f"tel:{normalized}"

    @staticmethod
    def _clean_query(
        value: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            value.strip(),
        )

    def _normalize_person_query(
        self,
        query: str,
    ) -> str:
        words = query.split()

        normalized = [
            self._normalize_name_word(
                word
            )
            for word in words
        ]

        return " ".join(
            normalized
        )

    @staticmethod
    def _normalize_name_word(
        word: str,
    ) -> str:
        lower = word.casefold()

        replacements = (
            ("овой", "ова"),
            ("евой", "ева"),
            ("иной", "ина"),
            ("ёвой", "ёва"),
        )

        for ending, replacement in replacements:
            if (
                lower.endswith(ending)
                and len(word) > len(ending)
            ):
                return (
                    word[:-len(ending)]
                    + replacement
                )

        if (
            lower.endswith("ию")
            and len(word) > 3
        ):
            return (
                word[:-2]
                + "ий"
            )

        if (
            lower.endswith("ии")
            and len(word) > 3
        ):
            return (
                word[:-2]
                + "ия"
            )

        if (
            lower.endswith("ье")
            and len(word) > 3
        ):
            return (
                word[:-2]
                + "ья"
            )

        if (
            lower.endswith("не")
            and len(word) > 4
        ):
            return (
                word[:-1]
                + "а"
            )

        if (
            lower.endswith("те")
            and len(word) > 4
        ):
            return (
                word[:-1]
                + "а"
            )

        if (
            lower.endswith("ле")
            and len(word) > 4
        ):
            return (
                word[:-1]
                + "а"
            )

        if (
            lower.endswith("у")
            and len(word) > 3
        ):
            return word[:-1]

        return word


contact_agent = ContactAgent(
    sim_card_tracker_client
)
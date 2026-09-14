import csv
import re
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "data" / "BD.csv"


LOOKALIKE_TRANSLATION = str.maketrans(
    {
        "a": "а",
        "b": "в",
        "c": "с",
        "e": "е",
        "h": "н",
        "k": "к",
        "m": "м",
        "o": "о",
        "p": "р",
        "t": "т",
        "x": "х",
        "y": "у",
    }
)


def normalize_text(value: str) -> str:
    value = (value or "").lower().replace("ё", "е")

    # Латинские символы, визуально совпадающие с кириллицей.
    # Например: M500 -> м500, C25 -> с25
    value = value.translate(LOOKALIKE_TRANSLATION)

    # М500, М-500, М 500 -> м500
    value = re.sub(
        r"\b([а-я])[\s\-]+(\d+)\b",
        r"\1\2",
        value,
    )

    # ЦЕМ II / A-П -> цем ii a-п и т.п.
    value = re.sub(
        r"[^а-яa-z0-9.+/%\-]+",
        " ",
        value,
        flags=re.IGNORECASE,
    )

    return " ".join(value.split())


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)

    return [
        token
        for token in normalized.split()
        if len(token) > 1
    ]


class ProductCatalog:
    def __init__(self) -> None:
        self.products: list[dict[str, Any]] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if not CATALOG_PATH.exists():
            raise FileNotFoundError(
                f"Файл товарной базы не найден: {CATALOG_PATH}"
            )

        with CATALOG_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter=";",
            )

            for index, row in enumerate(reader, start=1):
                name = (row.get("Название") or "").strip()
                description = (
                    row.get("Детальное описание") or ""
                ).strip()
                unit = (
                    row.get("Ед. измерения") or ""
                ).strip()

                availability = (
                    row.get("Доступность") or ""
                ).strip().lower()

                raw_price = (
                    row.get("Максимальная цена") or ""
                ).strip()

                try:
                    price = float(
                        raw_price.replace(",", ".")
                    )
                except ValueError:
                    price = None

                search_name = normalize_text(name)
                search_description = normalize_text(
                    description
                )

                self.products.append(
                    {
                        "id": index,
                        "name": name,
                        "description": description,
                        "price": price,
                        "unit": unit,
                        "available": availability == "да",
                        "_search_name": search_name,
                        "_search_description": search_description,
                        "_name_tokens": set(
                            tokenize(search_name)
                        ),
                        "_description_tokens": set(
                            tokenize(search_description)
                        ),
                    }
                )

        self._loaded = True

    def search(
        self,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        available_only: bool = True,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        self._ensure_loaded()

        query_normalized = normalize_text(query)

        if not query_normalized:
            return []

        query_tokens = set(
            tokenize(query_normalized)
        )

        scored_products: list[
            tuple[float, dict[str, Any]]
        ] = []

        for product in self.products:
            if (
                available_only
                and not product["available"]
            ):
                continue

            price = product["price"]

            if (
                min_price is not None
                and price is not None
                and price < min_price
            ):
                continue

            if (
                max_price is not None
                and price is not None
                and price > max_price
            ):
                continue

            name = product["_search_name"]
            description = product["_search_description"]

            name_tokens = product["_name_tokens"]
            description_tokens = (
                product["_description_tokens"]
            )

            score = 0.0

            # Самые сильные совпадения
            if query_normalized == name:
                score += 1000

            if query_normalized in name:
                score += 400

            if query_normalized in description:
                score += 120

            # Совпадения отдельных значимых токенов
            name_matches = (
                query_tokens & name_tokens
            )

            description_matches = (
                query_tokens & description_tokens
            )

            score += len(name_matches) * 80
            score += len(description_matches) * 18

            # Бонус, если все слова запроса встретились
            # в названии или описании
            combined_tokens = (
                name_tokens
                | description_tokens
            )

            if (
                query_tokens
                and query_tokens.issubset(
                    combined_tokens
                )
            ):
                score += 150

            # Если большая часть запроса попала в название
            if query_tokens:
                coverage = (
                    len(name_matches)
                    / len(query_tokens)
                )

                score += coverage * 120

            # Fuzzy matching оставляем как резерв
            score += (
                fuzz.token_set_ratio(
                    query_normalized,
                    name,
                )
                * 1.2
            )

            score += (
                fuzz.partial_ratio(
                    query_normalized,
                    name,
                )
                * 0.4
            )

            # Описание учитываем слабее,
            # чтобы длинные тексты не забивали название
            score += (
                fuzz.partial_ratio(
                    query_normalized,
                    description,
                )
                * 0.12
            )

            if score <= 0:
                continue

            scored_products.append(
                (
                    score,
                    product,
                )
            )

        scored_products.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = []

        for score, product in scored_products[:limit]:
            results.append(
                self._serialize_search_result(
                    product,
                    score,
                )
            )

        return results

    def get_product(
        self,
        product_id: int,
    ) -> dict[str, Any] | None:
        self._ensure_loaded()

        if product_id < 1:
            return None

        index = product_id - 1

        if index >= len(self.products):
            return None

        product = self.products[index]

        return self._serialize_product(
            product
        )

    def compare(
        self,
        product_ids: list[int],
    ) -> list[dict[str, Any]]:
        self._ensure_loaded()

        results = []

        for product_id in product_ids:
            product = self.get_product(
                product_id
            )

            if product is not None:
                results.append(product)

        return results

    def _serialize_search_result(
        self,
        product: dict[str, Any],
        score: float,
    ) -> dict[str, Any]:
        description = product["description"]

        if len(description) > 900:
            description = (
                description[:900].rstrip()
                + "..."
            )

        return {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "unit": product["unit"],
            "available": product["available"],
            "description": description,
            "relevance": round(
                score,
                2,
            ),
        }

    def _serialize_product(
        self,
        product: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "unit": product["unit"],
            "available": product["available"],
            "description": product["description"],
        }


product_catalog = ProductCatalog()
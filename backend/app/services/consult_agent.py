from typing import Any

from backend.app.services.product_catalog import (
    product_catalog,
)


class ConsultAgent:
    async def search_products(
        self,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        available_only: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:

        query = query.strip()

        if not query:
            return {
                "status": "error",
                "message": "Не задан поисковый запрос.",
                "results": [],
            }

        results = product_catalog.search(
            query=query,
            min_price=min_price,
            max_price=max_price,
            available_only=available_only,
            limit=limit,
        )

        return {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": results,
        }

    async def get_product(
        self,
        product_id: int,
    ) -> dict[str, Any]:

        product = product_catalog.get_product(
            product_id
        )

        if product is None:
            return {
                "status": "not_found",
                "message": (
                    f"Товар с id={product_id} "
                    "не найден."
                ),
            }

        return {
            "status": "ok",
            "product": product,
        }

    async def compare_products(
        self,
        product_ids: list[int],
    ) -> dict[str, Any]:

        products = product_catalog.compare(
            product_ids
        )

        if not products:
            return {
                "status": "not_found",
                "message": "Товары не найдены.",
                "products": [],
            }

        return {
            "status": "ok",
            "count": len(products),
            "products": products,
        }


consult_agent = ConsultAgent()
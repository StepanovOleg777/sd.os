import httpx

from backend.app.core.config import settings


class SimCardTrackerError(Exception):
    pass


class SimCardTrackerClient:
    def __init__(self) -> None:
        self.base_url = settings.SIM_CARD_TRACKER_API_URL
        self.token = settings.SIM_CARD_TRACKER_API_TOKEN

    async def search_contacts(
        self,
        query: str = "",
        department: str = "",
        position: str = "",
        location: str = "",
        supervisor: str = "",
        status: str = "",
    ) -> list[dict]:
        if not self.token:
            raise SimCardTrackerError(
                "Не задан SIM_CARD_TRACKER_API_TOKEN."
            )

        params = {}

        if query:
            params["q"] = query

        if department:
            params["department"] = department

        if position:
            params["position"] = position

        if location:
            params["location"] = location

        if supervisor:
            params["supervisor"] = supervisor

        if status:
            params["status"] = status

        if not params:
            raise SimCardTrackerError(
                "Не заданы параметры поиска."
            )

        url = (
            f"{self.base_url}"
            "/api/v1/contacts/search/"
        )

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
            ) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": (
                            f"Bearer {self.token}"
                        ),
                    },
                )

        except httpx.ConnectError as exc:
            raise SimCardTrackerError(
                "sim_card_tracker недоступен."
            ) from exc

        except httpx.TimeoutException as exc:
            raise SimCardTrackerError(
                "sim_card_tracker не ответил вовремя."
            ) from exc

        if response.status_code == 401:
            raise SimCardTrackerError(
                "sim_card_tracker отклонил авторизацию SD.OS."
            )

        if response.status_code != 200:
            raise SimCardTrackerError(
                "sim_card_tracker вернул ошибку "
                f"{response.status_code}: {response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SimCardTrackerError(
                "sim_card_tracker вернул некорректный JSON."
            ) from exc

        results = payload.get(
            "results",
            [],
        )

        if not isinstance(results, list):
            raise SimCardTrackerError(
                "Некорректный формат ответа sim_card_tracker."
            )

        return results


sim_card_tracker_client = SimCardTrackerClient()
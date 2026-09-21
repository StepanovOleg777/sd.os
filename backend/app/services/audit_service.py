from typing import Any

from fastapi import Request

from backend.app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def get_ip_address(
        request: Request | None,
    ) -> str | None:
        if request is None:
            return None

        forwarded_for = request.headers.get(
            "x-forwarded-for"
        )

        if forwarded_for:
            return (
                forwarded_for
                .split(",")[0]
                .strip()
            )

        real_ip = request.headers.get(
            "x-real-ip"
        )

        if real_ip:
            return real_ip.strip()

        if request.client is not None:
            return request.client.host

        return None

    @staticmethod
    def get_user_agent(
        request: Request | None,
    ) -> str | None:
        if request is None:
            return None

        return request.headers.get(
            "user-agent"
        )

    async def write(
        self,
        db,
        *,
        action: str,
        actor_user_id: int | None = None,
        target_user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=self.get_ip_address(
                request
            ),
            user_agent=self.get_user_agent(
                request
            ),
        )

        db.add(
            audit_log
        )

        return audit_log


audit_service = AuditService()
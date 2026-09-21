from datetime import datetime

from sqlalchemy import (
    func,
    or_,
    select,
)

from backend.app.models.department import Department
from backend.app.models.sd_chat import (
    ChatAnnouncement,
    ChatAnnouncementDepartment,
    ChatAnnouncementRecipient,
)
from backend.app.models.user import User
from backend.app.services.permission_service import (
    permission_service,
)


class SDAnnouncementService:

    # =========================================================
    # CHAT ACCESS
    # =========================================================

    async def user_has_chat_access(
        self,
        db,
        user_id: int,
    ) -> bool:
        return await permission_service.has_permission(
            db=db,
            user_id=user_id,
            permission_code="chat.use",
        )

    async def filter_users_with_chat_access(
        self,
        db,
        users: list[User],
    ) -> list[User]:
        allowed_users = []

        for user in users:
            has_chat_access = (
                await self.user_has_chat_access(
                    db,
                    user.id,
                )
            )

            if has_chat_access:
                allowed_users.append(
                    user
                )

        return allowed_users

    # =========================================================
    # USERS
    # =========================================================

    async def get_active_users(
        self,
        db,
    ) -> list[User]:
        result = await db.execute(
            select(User)
            .where(
                User.status == "active",
                User.is_active.is_(True),
            )
            .order_by(
                User.fio
            )
        )

        users = list(
            result.scalars().all()
        )

        return (
            await self.filter_users_with_chat_access(
                db,
                users,
            )
        )

    async def get_department_users(
        self,
        db,
        department_ids: list[int],
    ) -> list[User]:
        if not department_ids:
            return []

        result = await db.execute(
            select(User)
            .where(
                User.department_id.in_(
                    department_ids
                ),
                User.status == "active",
                User.is_active.is_(True),
            )
            .order_by(
                User.fio
            )
        )

        users = list(
            result.scalars().all()
        )

        return (
            await self.filter_users_with_chat_access(
                db,
                users,
            )
        )

    # =========================================================
    # DEPARTMENTS
    # =========================================================

    async def get_department(
        self,
        db,
        department_id: int,
    ) -> Department | None:
        result = await db.execute(
            select(Department)
            .where(
                Department.id == department_id
            )
        )

        return result.scalar_one_or_none()

    async def get_departments(
        self,
        db,
        department_ids: list[int],
    ) -> list[Department]:
        if not department_ids:
            return []

        unique_ids = list(
            dict.fromkeys(
                department_ids
            )
        )

        result = await db.execute(
            select(Department)
            .where(
                Department.id.in_(
                    unique_ids
                )
            )
            .order_by(
                Department.name
            )
        )

        return list(
            result.scalars().all()
        )

    async def get_announcement_departments(
        self,
        db,
        announcement_id: int,
    ) -> list[Department]:
        result = await db.execute(
            select(Department)
            .join(
                ChatAnnouncementDepartment,
                ChatAnnouncementDepartment.department_id
                == Department.id,
            )
            .where(
                ChatAnnouncementDepartment.announcement_id
                == announcement_id
            )
            .order_by(
                Department.name
            )
        )

        return list(
            result.scalars().all()
        )

    # =========================================================
    # CREATE COMPANY ANNOUNCEMENT
    # =========================================================

    async def create_company_announcement(
        self,
        db,
        *,
        author_user_id: int,
        text: str,
        requires_acknowledgement: bool = True,
        expires_at: datetime | None = None,
    ) -> ChatAnnouncement:
        text = text.strip()

        if not text:
            raise ValueError(
                "Текст объявления не может быть пустым."
            )

        if len(text) > 20000:
            raise ValueError(
                "Текст объявления слишком длинный."
            )

        users = await self.get_active_users(
            db
        )

        if not users:
            raise ValueError(
                "Нет активных пользователей "
                "с доступом к внутренним сообщениям."
            )

        announcement = ChatAnnouncement(
            author_user_id=author_user_id,
            audience_type="company",
            text=text,
            requires_acknowledgement=(
                requires_acknowledgement
            ),
            is_active=True,
            expires_at=expires_at,
        )

        db.add(
            announcement
        )

        await db.flush()

        delivered_at = datetime.utcnow()

        for user in users:
            db.add(
                ChatAnnouncementRecipient(
                    announcement_id=announcement.id,
                    user_id=user.id,
                    delivered_at=delivered_at,
                )
            )

        await db.flush()

        return announcement

    # =========================================================
    # CREATE DEPARTMENT ANNOUNCEMENT
    # =========================================================

    async def create_department_announcement(
        self,
        db,
        *,
        author_user_id: int,
        department_ids: list[int],
        text: str,
        requires_acknowledgement: bool = True,
        expires_at: datetime | None = None,
    ) -> ChatAnnouncement:
        text = text.strip()

        if not text:
            raise ValueError(
                "Текст объявления не может быть пустым."
            )

        if len(text) > 20000:
            raise ValueError(
                "Текст объявления слишком длинный."
            )

        if not department_ids:
            raise ValueError(
                "Не выбран ни один отдел."
            )

        unique_department_ids = list(
            dict.fromkeys(
                department_ids
            )
        )

        departments = (
            await self.get_departments(
                db,
                unique_department_ids,
            )
        )

        if (
            len(departments)
            != len(unique_department_ids)
        ):
            raise ValueError(
                "Один или несколько выбранных "
                "отделов не найдены."
            )

        inactive_departments = [
            department
            for department in departments
            if not department.is_active
        ]

        if inactive_departments:
            names = ", ".join(
                department.name
                for department in inactive_departments
            )

            raise ValueError(
                "Один или несколько отделов "
                f"отключены: {names}"
            )

        users = (
            await self.get_department_users(
                db,
                unique_department_ids,
            )
        )

        if not users:
            raise ValueError(
                "В выбранных отделах нет "
                "активных пользователей "
                "с доступом к внутренним сообщениям."
            )

        announcement = ChatAnnouncement(
            author_user_id=author_user_id,
            audience_type="departments",
            text=text,
            requires_acknowledgement=(
                requires_acknowledgement
            ),
            is_active=True,
            expires_at=expires_at,
        )

        db.add(
            announcement
        )

        await db.flush()

        for department_id in unique_department_ids:
            db.add(
                ChatAnnouncementDepartment(
                    announcement_id=announcement.id,
                    department_id=department_id,
                )
            )

        await db.flush()

        unique_users = {
            user.id: user
            for user in users
        }

        delivered_at = datetime.utcnow()

        for user in unique_users.values():
            db.add(
                ChatAnnouncementRecipient(
                    announcement_id=announcement.id,
                    user_id=user.id,
                    delivered_at=delivered_at,
                )
            )

        await db.flush()

        return announcement

    # =========================================================
    # USER ANNOUNCEMENTS
    # =========================================================

    async def get_user_announcements(
        self,
        db,
        *,
        user_id: int,
        unread_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        if limit < 1:
            limit = 1

        if limit > 200:
            limit = 200

        query = (
            select(
                ChatAnnouncementRecipient,
                ChatAnnouncement,
            )
            .join(
                ChatAnnouncement,
                ChatAnnouncement.id
                == ChatAnnouncementRecipient
                .announcement_id,
            )
            .where(
                ChatAnnouncementRecipient.user_id
                == user_id,
                ChatAnnouncement.is_active.is_(
                    True
                ),
                or_(
                    ChatAnnouncement.expires_at
                    .is_(None),
                    ChatAnnouncement.expires_at
                    > datetime.utcnow(),
                ),
            )
            .order_by(
                ChatAnnouncement.id.desc()
            )
            .limit(
                limit
            )
        )

        if unread_only:
            query = query.where(
                ChatAnnouncementRecipient.read_at
                .is_(None)
            )

        result = await db.execute(
            query
        )

        rows = result.all()

        items = []

        for (
            recipient,
            announcement,
        ) in rows:
            author_result = await db.execute(
                select(User)
                .where(
                    User.id
                    == announcement.author_user_id
                )
            )

            author = (
                author_result
                .scalar_one_or_none()
            )

            departments = (
                await self
                .get_announcement_departments(
                    db,
                    announcement.id,
                )
            )

            items.append(
                {
                    "announcement": announcement,
                    "recipient": recipient,
                    "author": author,
                    "departments": departments,
                }
            )

        return items

    # =========================================================
    # REQUIRED ANNOUNCEMENTS ON LOGIN
    # =========================================================

    async def get_pending_required_announcements(
        self,
        db,
        *,
        user_id: int,
        limit: int = 20,
    ) -> list[dict]:
        has_chat_access = (
            await self.user_has_chat_access(
                db,
                user_id,
            )
        )

        if not has_chat_access:
            return []

        if limit < 1:
            limit = 1

        if limit > 100:
            limit = 100

        result = await db.execute(
            select(
                ChatAnnouncementRecipient,
                ChatAnnouncement,
            )
            .join(
                ChatAnnouncement,
                ChatAnnouncement.id
                == ChatAnnouncementRecipient
                .announcement_id,
            )
            .where(
                ChatAnnouncementRecipient.user_id
                == user_id,
                ChatAnnouncementRecipient
                .acknowledged_at
                .is_(None),
                ChatAnnouncement
                .requires_acknowledgement
                .is_(True),
                ChatAnnouncement.is_active.is_(
                    True
                ),
                or_(
                    ChatAnnouncement.expires_at
                    .is_(None),
                    ChatAnnouncement.expires_at
                    > datetime.utcnow(),
                ),
            )
            .order_by(
                ChatAnnouncement.created_at.asc()
            )
            .limit(
                limit
            )
        )

        rows = result.all()

        items = []

        for (
            recipient,
            announcement,
        ) in rows:
            author_result = await db.execute(
                select(User)
                .where(
                    User.id
                    == announcement.author_user_id
                )
            )

            author = (
                author_result
                .scalar_one_or_none()
            )

            departments = (
                await self
                .get_announcement_departments(
                    db,
                    announcement.id,
                )
            )

            items.append(
                {
                    "announcement": announcement,
                    "recipient": recipient,
                    "author": author,
                    "departments": departments,
                }
            )

        return items

    # =========================================================
    # RECIPIENT
    # =========================================================

    async def get_recipient(
        self,
        db,
        *,
        announcement_id: int,
        user_id: int,
    ) -> ChatAnnouncementRecipient | None:
        result = await db.execute(
            select(
                ChatAnnouncementRecipient
            )
            .where(
                ChatAnnouncementRecipient
                .announcement_id
                == announcement_id,
                ChatAnnouncementRecipient.user_id
                == user_id,
            )
        )

        return result.scalar_one_or_none()

    # =========================================================
    # READ
    # =========================================================

    async def mark_read(
        self,
        db,
        *,
        announcement_id: int,
        user_id: int,
    ) -> ChatAnnouncementRecipient:
        recipient = await self.get_recipient(
            db,
            announcement_id=announcement_id,
            user_id=user_id,
        )

        if recipient is None:
            raise PermissionError(
                "Объявление недоступно пользователю."
            )

        if recipient.read_at is None:
            recipient.read_at = datetime.utcnow()

        await db.flush()

        return recipient

    # =========================================================
    # ACKNOWLEDGE
    # =========================================================

    async def acknowledge(
        self,
        db,
        *,
        announcement_id: int,
        user_id: int,
    ) -> ChatAnnouncementRecipient:
        recipient = await self.get_recipient(
            db,
            announcement_id=announcement_id,
            user_id=user_id,
        )

        if recipient is None:
            raise PermissionError(
                "Объявление недоступно пользователю."
            )

        announcement_result = await db.execute(
            select(ChatAnnouncement)
            .where(
                ChatAnnouncement.id
                == announcement_id
            )
        )

        announcement = (
            announcement_result
            .scalar_one_or_none()
        )

        if announcement is None:
            raise ValueError(
                "Объявление не найдено."
            )

        if (
            not announcement
            .requires_acknowledgement
        ):
            raise ValueError(
                "Это объявление не требует подтверждения."
            )

        now = datetime.utcnow()

        if recipient.read_at is None:
            recipient.read_at = now

        if recipient.acknowledged_at is None:
            recipient.acknowledged_at = now

        await db.flush()

        return recipient

    # =========================================================
    # COUNTERS
    # =========================================================

    async def get_unread_count(
        self,
        db,
        *,
        user_id: int,
    ) -> int:
        result = await db.execute(
            select(
                func.count(
                    ChatAnnouncementRecipient.id
                )
            )
            .join(
                ChatAnnouncement,
                ChatAnnouncement.id
                == ChatAnnouncementRecipient
                .announcement_id,
            )
            .where(
                ChatAnnouncementRecipient.user_id
                == user_id,
                ChatAnnouncementRecipient.read_at
                .is_(None),
                ChatAnnouncement.is_active.is_(
                    True
                ),
                or_(
                    ChatAnnouncement.expires_at
                    .is_(None),
                    ChatAnnouncement.expires_at
                    > datetime.utcnow(),
                ),
            )
        )

        return result.scalar_one()

    async def get_required_ack_count(
        self,
        db,
        *,
        user_id: int,
    ) -> int:
        result = await db.execute(
            select(
                func.count(
                    ChatAnnouncementRecipient.id
                )
            )
            .join(
                ChatAnnouncement,
                ChatAnnouncement.id
                == ChatAnnouncementRecipient
                .announcement_id,
            )
            .where(
                ChatAnnouncementRecipient.user_id
                == user_id,
                ChatAnnouncementRecipient
                .acknowledged_at
                .is_(None),
                ChatAnnouncement
                .requires_acknowledgement
                .is_(True),
                ChatAnnouncement.is_active.is_(
                    True
                ),
                or_(
                    ChatAnnouncement.expires_at
                    .is_(None),
                    ChatAnnouncement.expires_at
                    > datetime.utcnow(),
                ),
            )
        )

        return result.scalar_one()

    # =========================================================
    # STATISTICS
    # =========================================================

    async def get_announcement_stats(
        self,
        db,
        *,
        announcement_id: int,
    ) -> dict:
        delivered_result = await db.execute(
            select(
                func.count(
                    ChatAnnouncementRecipient.id
                )
            )
            .where(
                ChatAnnouncementRecipient
                .announcement_id
                == announcement_id
            )
        )

        read_result = await db.execute(
            select(
                func.count(
                    ChatAnnouncementRecipient.id
                )
            )
            .where(
                ChatAnnouncementRecipient
                .announcement_id
                == announcement_id,
                ChatAnnouncementRecipient.read_at
                .is_not(None),
            )
        )

        acknowledged_result = await db.execute(
            select(
                func.count(
                    ChatAnnouncementRecipient.id
                )
            )
            .where(
                ChatAnnouncementRecipient
                .announcement_id
                == announcement_id,
                ChatAnnouncementRecipient
                .acknowledged_at
                .is_not(None),
            )
        )

        delivered = (
            delivered_result.scalar_one()
        )

        read = (
            read_result.scalar_one()
        )

        acknowledged = (
            acknowledged_result.scalar_one()
        )

        return {
            "delivered": delivered,
            "read": read,
            "unread": max(
                delivered - read,
                0,
            ),
            "acknowledged": acknowledged,
            "not_acknowledged": max(
                delivered - acknowledged,
                0,
            ),
        }


sd_announcement_service = (
    SDAnnouncementService()
)
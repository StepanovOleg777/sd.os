from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import select

from backend.app.core.config import (
    TEMPLATES_DIR,
    settings,
)
from backend.app.core.database import (
    AsyncSessionLocal,
)
from backend.app.core.permissions import (
    require_permission,
)
from backend.app.models.department import Department
from backend.app.models.user import User
from backend.app.services.permission_service import (
    permission_service,
)
from backend.app.services.sd_announcement_service import (
    sd_announcement_service,
)
from backend.app.services.sd_chat_service import (
    sd_chat_service,
)


router = APIRouter(
    tags=["sd-chat"],
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


# =========================================================
# REQUEST MODELS
# =========================================================


class DirectConversationCreateRequest(
    BaseModel
):
    user_id: int = Field(
        ...,
        gt=0,
    )


class MessageCreateRequest(
    BaseModel
):
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


class MarkReadRequest(
    BaseModel
):
    message_id: int = Field(
        ...,
        gt=0,
    )


class CompanyAnnouncementCreateRequest(
    BaseModel
):
    text: str = Field(
        ...,
        min_length=1,
        max_length=20000,
    )

    requires_acknowledgement: bool = True

    expires_at: datetime | None = None


class DepartmentAnnouncementCreateRequest(
    BaseModel
):
    department_ids: list[int] = Field(
        ...,
        min_length=1,
    )

    text: str = Field(
        ...,
        min_length=1,
        max_length=20000,
    )

    requires_acknowledgement: bool = True

    expires_at: datetime | None = None


# =========================================================
# HELPERS
# =========================================================


def user_to_dict(
    user: User | None,
) -> dict | None:
    if user is None:
        return None

    return {
        "id": user.id,
        "fio": user.fio,
        "department_id": user.department_id,
    }


def department_to_dict(
    department: Department | None,
) -> dict | None:
    if department is None:
        return None

    return {
        "id": department.id,
        "name": department.name,
        "is_active": department.is_active,
    }


def message_to_dict(
    message,
) -> dict:
    return {
        "id": message.id,
        "conversation_id": (
            message.conversation_id
        ),
        "sender_user_id": (
            message.sender_user_id
        ),
        "message_type": (
            message.message_type
        ),
        "text": message.text,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at
            else None
        ),
        "edited_at": (
            message.edited_at.isoformat()
            if message.edited_at
            else None
        ),
        "is_deleted": (
            message.is_deleted
        ),
    }


def announcement_to_dict(
    *,
    announcement,
    recipient=None,
    author=None,
    departments=None,
) -> dict:
    departments = departments or []

    return {
        "id": announcement.id,

        "author": (
            user_to_dict(
                author
            )
        ),

        "author_user_id": (
            announcement.author_user_id
        ),

        "audience_type": (
            announcement.audience_type
        ),

        "departments": [
            department_to_dict(
                department
            )
            for department in departments
        ],

        "department_ids": [
            department.id
            for department in departments
        ],

        "text": (
            announcement.text
        ),

        "requires_acknowledgement": (
            announcement
            .requires_acknowledgement
        ),

        "is_active": (
            announcement.is_active
        ),

        "created_at": (
            announcement.created_at.isoformat()
            if announcement.created_at
            else None
        ),

        "expires_at": (
            announcement.expires_at.isoformat()
            if announcement.expires_at
            else None
        ),

        "recipient": (
            {
                "delivered_at": (
                    recipient.delivered_at.isoformat()
                    if (
                        recipient
                        and recipient.delivered_at
                    )
                    else None
                ),

                "read_at": (
                    recipient.read_at.isoformat()
                    if (
                        recipient
                        and recipient.read_at
                    )
                    else None
                ),

                "acknowledged_at": (
                    recipient
                    .acknowledged_at
                    .isoformat()
                    if (
                        recipient
                        and recipient
                        .acknowledged_at
                    )
                    else None
                ),
            }
            if recipient is not None
            else None
        ),
    }


async def ensure_recipient_available(
    db,
    *,
    actor: User,
    recipient_user_id: int,
) -> User:
    if recipient_user_id == actor.id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Нельзя создать личный диалог "
                "с самим собой."
            ),
        )

    result = await db.execute(
        select(User).where(
            User.id == recipient_user_id,
            User.status == "active",
            User.is_active.is_(True),
        )
    )

    recipient = (
        result.scalar_one_or_none()
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Пользователь не найден "
                "или его учётная запись "
                "неактивна."
            ),
        )

    recipient_has_chat = (
        await permission_service
        .has_permission(
            db=db,
            user_id=recipient.id,
            permission_code="chat.use",
        )
    )

    if not recipient_has_chat:
        raise HTTPException(
            status_code=400,
            detail=(
                "У выбранного пользователя "
                "нет доступа к внутренним "
                "сообщениям."
            ),
        )

    return recipient


# =========================================================
# PAGE
# =========================================================


@router.get(
    "/sd-chat",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def sd_chat_page(
    request: Request,
    current_user: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        can_access_admin = (
            await permission_service
            .has_permission(
                db=db,
                user_id=current_user.id,
                permission_code="users.view",
            )
        )

        can_announce_company = (
            await permission_service
            .has_permission(
                db=db,
                user_id=current_user.id,
                permission_code=(
                    "chat.announcement.company"
                ),
            )
        )

        can_announce_department = (
            await permission_service
            .has_permission(
                db=db,
                user_id=current_user.id,
                permission_code=(
                    "chat.announcement.department"
                ),
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="sd_chat/index.html",
        context={
            "current_user": current_user,
            "app_version": settings.APP_VERSION,
            "can_access_admin": (
                can_access_admin
            ),
            "can_announce_company": (
                can_announce_company
            ),
            "can_announce_department": (
                can_announce_department
            ),
        },
    )


# =========================================================
# USERS
# =========================================================


@router.get(
    "/api/sd-chat/users",
)
async def search_chat_users(
    q: str = Query(
        "",
        max_length=100,
    ),
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    q = q.strip()

    async with AsyncSessionLocal() as db:
        query = (
            select(User)
            .where(
                User.id != actor.id,
                User.status == "active",
                User.is_active.is_(True),
            )
            .order_by(
                User.fio
            )
            .limit(50)
        )

        if q:
            query = (
                select(User)
                .where(
                    User.id != actor.id,
                    User.status == "active",
                    User.is_active.is_(True),
                    User.fio.ilike(
                        f"%{q}%"
                    ),
                )
                .order_by(
                    User.fio
                )
                .limit(50)
            )

        result = await db.execute(
            query
        )

        users = list(
            result.scalars().all()
        )

        available_users = []

        for user in users:
            has_chat = (
                await permission_service
                .has_permission(
                    db=db,
                    user_id=user.id,
                    permission_code="chat.use",
                )
            )

            if not has_chat:
                continue

            available_users.append(
                user_to_dict(
                    user
                )
            )

    return {
        "users": available_users,
    }


# =========================================================
# CONVERSATIONS
# =========================================================


@router.get(
    "/api/sd-chat/conversations",
)
async def get_conversations(
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        items = (
            await sd_chat_service
            .get_user_conversations(
                db,
                user_id=actor.id,
            )
        )

        conversations = []

        for item in items:
            conversation = (
                item["conversation"]
            )

            last_message = (
                item["last_message"]
            )

            conversations.append(
                {
                    "id": conversation.id,

                    "conversation_type": (
                        conversation
                        .conversation_type
                    ),

                    "title": (
                        conversation.title
                    ),

                    "other_user": (
                        user_to_dict(
                            item[
                                "other_user"
                            ]
                        )
                    ),

                    "last_message": (
                        message_to_dict(
                            last_message
                        )
                        if last_message
                        else None
                    ),

                    "unread_count": (
                        item[
                            "unread_count"
                        ]
                    ),

                    "created_at": (
                        conversation
                        .created_at
                        .isoformat()
                        if conversation.created_at
                        else None
                    ),

                    "updated_at": (
                        conversation
                        .updated_at
                        .isoformat()
                        if conversation.updated_at
                        else None
                    ),
                }
            )

    return {
        "conversations": conversations,
    }


@router.post(
    "/api/sd-chat/direct",
    status_code=status.HTTP_200_OK,
)
async def create_direct_conversation(
    payload: DirectConversationCreateRequest,
    actor: User = Depends(
        require_permission(
            "chat.message.send"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        await ensure_recipient_available(
            db,
            actor=actor,
            recipient_user_id=(
                payload.user_id
            ),
        )

        try:
            conversation = (
                await sd_chat_service
                .get_or_create_direct_conversation(
                    db,
                    user_id=actor.id,
                    other_user_id=(
                        payload.user_id
                    ),
                )
            )

            await db.commit()

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "conversation_id": (
            conversation.id
        ),
    }


# =========================================================
# MESSAGES
# =========================================================


@router.get(
    "/api/sd-chat/conversations/{conversation_id}/messages",
)
async def get_messages(
    conversation_id: int,
    limit: int = Query(
        100,
        ge=1,
        le=200,
    ),
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            messages = (
                await sd_chat_service
                .get_messages(
                    db,
                    conversation_id=(
                        conversation_id
                    ),
                    user_id=actor.id,
                    limit=limit,
                )
            )

        except PermissionError as exc:
            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        conversation = (
            await sd_chat_service
            .get_conversation(
                db,
                conversation_id,
            )
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Диалог не найден.",
            )

        other_user = None

        if (
            conversation.conversation_type
            == "direct"
        ):
            other_user = (
                await sd_chat_service
                .get_other_user(
                    db,
                    conversation_id=(
                        conversation_id
                    ),
                    user_id=actor.id,
                )
            )

    return {
        "conversation": {
            "id": (
                conversation.id
            ),

            "conversation_type": (
                conversation
                .conversation_type
            ),

            "title": (
                conversation.title
            ),

            "other_user": (
                user_to_dict(
                    other_user
                )
            ),
        },

        "messages": [
            message_to_dict(
                message
            )
            for message in messages
        ],
    }


@router.post(
    "/api/sd-chat/conversations/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    payload: MessageCreateRequest,
    actor: User = Depends(
        require_permission(
            "chat.message.send"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            message = (
                await sd_chat_service
                .send_message(
                    db,
                    conversation_id=(
                        conversation_id
                    ),
                    sender_user_id=(
                        actor.id
                    ),
                    text=payload.text,
                )
            )

            await db.commit()

        except PermissionError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "message": (
            message_to_dict(
                message
            )
        ),
    }


# =========================================================
# MESSAGE READ STATE
# =========================================================


@router.post(
    "/api/sd-chat/conversations/{conversation_id}/read",
)
async def mark_conversation_read(
    conversation_id: int,
    payload: MarkReadRequest,
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            await sd_chat_service.mark_as_read(
                db,
                conversation_id=conversation_id,
                user_id=actor.id,
                message_id=payload.message_id,
            )

            await db.commit()

        except PermissionError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "ok": True,
    }


# =========================================================
# ANNOUNCEMENTS — USER LIST
# =========================================================


@router.get(
    "/api/sd-chat/announcements",
)
async def get_announcements(
    unread_only: bool = Query(
        False
    ),
    limit: int = Query(
        100,
        ge=1,
        le=200,
    ),
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        items = (
            await sd_announcement_service
            .get_user_announcements(
                db,
                user_id=actor.id,
                unread_only=(
                    unread_only
                ),
                limit=limit,
            )
        )

        announcements = []

        for item in items:
            announcements.append(
                announcement_to_dict(
                    announcement=(
                        item["announcement"]
                    ),

                    recipient=(
                        item["recipient"]
                    ),

                    author=(
                        item["author"]
                    ),

                    departments=(
                        item["departments"]
                    ),
                )
            )

    return {
        "announcements": announcements,
    }


# =========================================================
# ANNOUNCEMENTS — AVAILABLE DEPARTMENTS
# =========================================================


@router.get(
    "/api/sd-chat/announcement-departments",
)
async def get_announcement_departments(
    actor: User = Depends(
        require_permission(
            "chat.announcement.department"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Department)
            .where(
                Department.is_active.is_(
                    True
                )
            )
            .order_by(
                Department.name
            )
        )

        departments = list(
            result.scalars().all()
        )

        allowed_departments = []

        for department in departments:
            allowed = (
                await permission_service
                .can_access(
                    db=db,
                    user_id=actor.id,
                    permission_code=(
                        "chat.announcement.department"
                    ),
                    target_department_id=(
                        department.id
                    ),
                )
            )

            if not allowed:
                continue

            allowed_departments.append(
                department_to_dict(
                    department
                )
            )

    return {
        "departments": allowed_departments,
    }


# =========================================================
# ANNOUNCEMENTS — CREATE COMPANY
# =========================================================


@router.post(
    "/api/sd-chat/announcements/company",
    status_code=status.HTTP_201_CREATED,
)
async def create_company_announcement(
    payload: CompanyAnnouncementCreateRequest,
    actor: User = Depends(
        require_permission(
            "chat.announcement.company"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            announcement = (
                await sd_announcement_service
                .create_company_announcement(
                    db,
                    author_user_id=(
                        actor.id
                    ),
                    text=(
                        payload.text
                    ),
                    requires_acknowledgement=(
                        payload
                        .requires_acknowledgement
                    ),
                    expires_at=(
                        payload.expires_at
                    ),
                )
            )

            await db.commit()

            stats = (
                await sd_announcement_service
                .get_announcement_stats(
                    db,
                    announcement_id=(
                        announcement.id
                    ),
                )
            )

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "announcement": (
            announcement_to_dict(
                announcement=(
                    announcement
                ),
                author=actor,
                departments=[],
            )
        ),

        "stats": stats,
    }


# =========================================================
# ANNOUNCEMENTS — CREATE DEPARTMENTS
# =========================================================


@router.post(
    "/api/sd-chat/announcements/departments",
    status_code=status.HTTP_201_CREATED,
)
async def create_departments_announcement(
    payload: DepartmentAnnouncementCreateRequest,
    actor: User = Depends(
        require_permission(
            "chat.announcement.department"
        )
    ),
):
    unique_department_ids = list(
        dict.fromkeys(
            payload.department_ids
        )
    )

    if not unique_department_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Не выбран ни один отдел."
            ),
        )

    async with AsyncSessionLocal() as db:

        # -------------------------------------------------
        # Проверяем право на КАЖДЫЙ выбранный отдел
        # -------------------------------------------------

        for department_id in unique_department_ids:
            allowed = (
                await permission_service
                .can_access(
                    db=db,
                    user_id=actor.id,
                    permission_code=(
                        "chat.announcement.department"
                    ),
                    target_department_id=(
                        department_id
                    ),
                )
            )

            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Нет права публиковать "
                        "объявление в один или "
                        "несколько выбранных отделов."
                    ),
                )

        try:
            announcement = (
                await sd_announcement_service
                .create_department_announcement(
                    db,
                    author_user_id=(
                        actor.id
                    ),
                    department_ids=(
                        unique_department_ids
                    ),
                    text=(
                        payload.text
                    ),
                    requires_acknowledgement=(
                        payload
                        .requires_acknowledgement
                    ),
                    expires_at=(
                        payload.expires_at
                    ),
                )
            )

            await db.commit()

            departments = (
                await sd_announcement_service
                .get_announcement_departments(
                    db,
                    announcement.id,
                )
            )

            stats = (
                await sd_announcement_service
                .get_announcement_stats(
                    db,
                    announcement_id=(
                        announcement.id
                    ),
                )
            )

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "announcement": (
            announcement_to_dict(
                announcement=(
                    announcement
                ),
                author=actor,
                departments=departments,
            )
        ),

        "stats": stats,
    }


# =========================================================
# ANNOUNCEMENTS — PENDING REQUIRED
# =========================================================


@router.get(
    "/api/sd-chat/announcements/pending-required",
)
async def get_pending_required_announcements(
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        items = (
            await sd_announcement_service
            .get_pending_required_announcements(
                db,
                user_id=actor.id,
            )
        )

        announcements = []

        for item in items:
            announcements.append(
                announcement_to_dict(
                    announcement=(
                        item["announcement"]
                    ),
                    recipient=(
                        item["recipient"]
                    ),
                    author=(
                        item["author"]
                    ),
                    departments=(
                        item["departments"]
                    ),
                )
            )

    return {
        "announcements": announcements,
    }


# =========================================================
# ANNOUNCEMENTS — READ
# =========================================================


@router.post(
    "/api/sd-chat/announcements/{announcement_id}/read",
)
async def mark_announcement_read(
    announcement_id: int,
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            recipient = (
                await sd_announcement_service
                .mark_read(
                    db,
                    announcement_id=(
                        announcement_id
                    ),
                    user_id=actor.id,
                )
            )

            await db.commit()

        except PermissionError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "ok": True,

        "read_at": (
            recipient.read_at.isoformat()
            if recipient.read_at
            else None
        ),
    }


# =========================================================
# ANNOUNCEMENTS — ACKNOWLEDGE
# =========================================================


@router.post(
    "/api/sd-chat/announcements/{announcement_id}/acknowledge",
)
async def acknowledge_announcement(
    announcement_id: int,
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        try:
            recipient = (
                await sd_announcement_service
                .acknowledge(
                    db,
                    announcement_id=(
                        announcement_id
                    ),
                    user_id=actor.id,
                )
            )

            await db.commit()

        except PermissionError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=403,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            await db.rollback()

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            await db.rollback()
            raise

    return {
        "ok": True,

        "read_at": (
            recipient.read_at.isoformat()
            if recipient.read_at
            else None
        ),

        "acknowledged_at": (
            recipient
            .acknowledged_at
            .isoformat()
            if recipient.acknowledged_at
            else None
        ),
    }


# =========================================================
# ANNOUNCEMENTS — COUNTERS
# =========================================================


@router.get(
    "/api/sd-chat/announcement-counts",
)
async def get_announcement_counts(
    actor: User = Depends(
        require_permission(
            "chat.use"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        unread = (
            await sd_announcement_service
            .get_unread_count(
                db,
                user_id=actor.id,
            )
        )

        requires_acknowledgement = (
            await sd_announcement_service
            .get_required_ack_count(
                db,
                user_id=actor.id,
            )
        )

    return {
        "unread": unread,

        "requires_acknowledgement": (
            requires_acknowledgement
        ),
    }
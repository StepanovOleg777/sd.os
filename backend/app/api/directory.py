from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.app.core.auth import get_current_user
from backend.app.core.config import (
    TEMPLATES_DIR,
    settings,
)
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.policies.data_access import (
    filter_directory_contacts,
)
from backend.app.services.permission_service import (
    permission_service,
)
from backend.app.services.sim_card_tracker_client import (
    SimCardTrackerError,
    sim_card_tracker_client,
)


router = APIRouter(
    tags=["directory"],
)


templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


# =========================================================
# PAGE
# =========================================================


@router.get(
    "/directory",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def directory_page(
    request: Request,
    current_user: User = Depends(
        get_current_user
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

        can_view_personal_phone = (
            await permission_service
            .has_permission(
                db=db,
                user_id=current_user.id,
                permission_code=(
                    "directory.personal_phone.view"
                ),
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="directory/index.html",
        context={
            "current_user": current_user,
            "app_version": settings.APP_VERSION,
            "can_access_admin": (
                can_access_admin
            ),
            "can_view_personal_phone": (
                can_view_personal_phone
            ),
        },
    )


# =========================================================
# SEARCH
# =========================================================


@router.get(
    "/api/directory/search",
)
async def search_directory(
    q: str = Query(
        "",
        max_length=200,
    ),
    department: str = Query(
        "",
        max_length=200,
    ),
    position: str = Query(
        "",
        max_length=200,
    ),
    location: str = Query(
        "",
        max_length=200,
    ),
    supervisor: str = Query(
        "",
        max_length=200,
    ),
    status: str = Query(
        "working",
        max_length=50,
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        contacts = (
            await sim_card_tracker_client
            .search_contacts(
                query=q.strip(),
                department=department.strip(),
                position=position.strip(),
                location=location.strip(),
                supervisor=supervisor.strip(),
                status=status.strip(),
            )
        )

    except SimCardTrackerError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Корпоративный справочник "
                "временно недоступен."
            ),
        ) from exc

    async with AsyncSessionLocal() as db:
        contacts = (
            await filter_directory_contacts(
                db=db,
                user_id=current_user.id,
                contacts=contacts,
            )
        )

    return {
        "count": len(contacts),
        "results": contacts,
    }
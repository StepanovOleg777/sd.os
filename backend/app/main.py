from fastapi import (
    Depends,
    FastAPI,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.api import sd_chat
from backend.app.api.admin import (
    router as admin_router,
)
from backend.app.api.auth import (
    router as auth_router,
)
from backend.app.api.chat import (
    router as chat_router,
)
from backend.app.api.invite import (
    router as invite_router,
)
from backend.app.api.password_reset import (
    router as password_reset_router,
)
from backend.app.api.voice import (
    router as voice_router,
)
from backend.app.core.auth import (
    get_optional_current_user,
)
from backend.app.core.config import (
    STATIC_DIR,
    TEMPLATES_DIR,
    settings,
)
from backend.app.core.database import (
    AsyncSessionLocal,
)
from backend.app.models.user import User
from backend.app.services.permission_service import (
    permission_service,
)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)


templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(invite_router)
app.include_router(password_reset_router)
app.include_router(sd_chat.router)


@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def index(
    request: Request,
    user: User | None = Depends(
        get_optional_current_user
    ),
):
    if user is None:
        return RedirectResponse(
            url="/login",
            status_code=302,
        )

    async with AsyncSessionLocal() as db:
        can_access_admin = (
            await permission_service
            .has_permission(
                db=db,
                user_id=user.id,
                permission_code="users.view",
            )
        )

        can_use_sd_chat = (
            await permission_service
            .has_permission(
                db=db,
                user_id=user.id,
                permission_code="chat.use",
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "user": user,
            "can_access_admin": (
                can_access_admin
            ),
            "can_use_sd_chat": (
                can_use_sd_chat
            ),
        },
    )


@app.get(
    "/login",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def login_page(
    request: Request,
    user: User | None = Depends(
        get_optional_current_user
    ),
):
    if user is not None:
        return RedirectResponse(
            url="/",
            status_code=302,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
        },
    )


@app.get(
    "/api/health",
    tags=["system"],
)
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
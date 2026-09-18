from fastapi import Depends

from fastapi import (
    APIRouter,
    Cookie,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.auth import get_current_user
from backend.app.core.security import hash_token
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.services.auth_service import (
    AuthError,
    auth_service,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


SESSION_COOKIE_NAME = "sdos_session"


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
):
    try:
        user, raw_token = (
            await auth_service.authenticate(
                payload.username.strip(),
                payload.password,
            )
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24,
        path="/",
    )

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "fio": user.fio,
            "email": user.email,
            "username": user.username,
        },
    }


@router.post("/logout")
async def logout(
    response: Response,
    sdos_session: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
):
    if sdos_session:
        token_hash = hash_token(
            sdos_session
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(
                    Session.token_hash
                    == token_hash
                )
            )

            session = (
                result.scalar_one_or_none()
            )

            if session is not None:
                await db.delete(
                    session
                )

                await db.commit()

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    return {
        "status": "ok",
    }


@router.get("/me")
async def me(
    user: User = Depends(
        get_current_user
    ),
):
    return {
        "id": user.id,
        "fio": user.fio,
        "email": user.email,
        "username": user.username,
    }

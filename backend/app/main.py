from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.api.chat import router as chat_router
from backend.app.api.voice import router as voice_router
from backend.app.core.config import (
    STATIC_DIR,
    TEMPLATES_DIR,
    settings,
)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


templates = Jinja2Templates(
    directory=TEMPLATES_DIR,
)


app.include_router(chat_router)
app.include_router(voice_router)


@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
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
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.services.speech_to_text_service import (
    speech_to_text_service,
)


router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
)


class TranscriptionResponse(BaseModel):
    text: str


ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/aac",
    "audio/3gpp",
    "audio/3gpp2",
}

MAX_AUDIO_SIZE = 25 * 1024 * 1024


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
)
async def transcribe_audio(
    audio: UploadFile = File(...),
) -> TranscriptionResponse:

    content_type = (
        audio.content_type
        or ""
    ).split(";")[0].strip().lower()

    if (
        content_type
        and content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=415,
            detail=f"Неподдерживаемый формат аудио: {audio.content_type}",
        )

    audio_data = await audio.read()

    if not audio_data:
        raise HTTPException(
            status_code=400,
            detail="Аудиофайл пуст.",
        )

    if len(audio_data) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Аудиофайл слишком большой.",
        )

    suffix = Path(
        audio.filename or "voice.webm"
    ).suffix or ".webm"

    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_file.write(audio_data)
            temp_path = Path(temp_file.name)

        text = speech_to_text_service.transcribe(
            temp_path
        )

        if not text:
            raise HTTPException(
                status_code=422,
                detail="Не удалось распознать речь.",
            )

        return TranscriptionResponse(
            text=text,
        )

    finally:
        await audio.close()

        if (
            temp_path
            and temp_path.exists()
        ):
            temp_path.unlink(
                missing_ok=True
            )
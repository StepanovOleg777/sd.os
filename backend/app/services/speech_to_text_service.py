from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

from backend.app.core.config import settings


class SpeechToTextService:
    """
    Локальный сервис распознавания речи.

    Модель загружается лениво при первом запросе,
    а затем остаётся в памяти процесса.
    """

    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._model_lock = Lock()

    def _get_model(self) -> WhisperModel:
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is None:
                self._model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE,
                )

        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()

        segments, _ = model.transcribe(
            str(audio_path),
            language="ru",
            beam_size=5,
            vad_filter=True,
        )

        text_parts = [
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ]

        return " ".join(text_parts).strip()


speech_to_text_service = SpeechToTextService()
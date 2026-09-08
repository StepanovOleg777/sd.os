import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(BASE_DIR / ".env")

FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"


class Settings:
    APP_NAME = "SD.OS"
    APP_VERSION = "0.1.0"

    DEBUG = os.getenv(
        "DEBUG",
        "true",
    ).lower() == "true"

    WHISPER_MODEL = os.getenv(
        "WHISPER_MODEL",
        "small",
    )

    WHISPER_DEVICE = os.getenv(
        "WHISPER_DEVICE",
        "cpu",
    )

    WHISPER_COMPUTE_TYPE = os.getenv(
        "WHISPER_COMPUTE_TYPE",
        "int8",
    )


settings = Settings()
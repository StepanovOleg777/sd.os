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

    SIM_CARD_TRACKER_API_URL = os.getenv(
        "SIM_CARD_TRACKER_API_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")

    SIM_CARD_TRACKER_API_TOKEN = os.getenv(
        "SIM_CARD_TRACKER_API_TOKEN",
        "",
    )

    OPENAI_API_KEY = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-5.6-luna",
    )

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "",
    )


settings = Settings()
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

    SMTP_HOST = os.getenv(
        "SMTP_HOST",
        "",
    )

    SMTP_PORT = int(
        os.getenv(
            "SMTP_PORT",
            "465",
        )
    )

    SMTP_USERNAME = os.getenv(
        "SMTP_USERNAME",
        "",
    )

    SMTP_PASSWORD = os.getenv(
        "SMTP_PASSWORD",
        "",
    )

    SMTP_FROM_EMAIL = os.getenv(
        "SMTP_FROM_EMAIL",
        "",
    )

    SMTP_FROM_NAME = os.getenv(
        "SMTP_FROM_NAME",
        "SD.OS",
    )

    SMTP_USE_SSL = (
        os.getenv(
            "SMTP_USE_SSL",
            "true",
        ).lower()
        == "true"
    )

    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    PASSWORD_RESET_TTL_MINUTES = int(
        os.getenv(
            "PASSWORD_RESET_TTL_MINUTES",
            "30",
        )
    )


settings = Settings()
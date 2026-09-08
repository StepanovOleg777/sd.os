from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]

FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"


class Settings:
    APP_NAME = "SD.OS"
    APP_VERSION = "0.1.0"
    DEBUG = True


settings = Settings()
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-ai-life-assistant-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "assistant.db"))
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    TESTING = False


class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    DEBUG = False
    DATABASE_PATH = ":memory:"
    GEMINI_API_KEY = ""

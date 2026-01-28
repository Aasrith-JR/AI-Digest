"""
Loads and handles config
"""
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import yaml


class Config(BaseModel):
    # Core
    DATABASE_PATH: str
    FAISS_INDEX_PATH: str

    # Ollama
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str

    # Personas
    PERSONA_GENAI_NEWS_ENABLED: bool = False
    PERSONA_PRODUCT_IDEAS_ENABLED: bool = False

    GENAI_NEWS_MIN_RELEVANCE: float = 0.0
    PRODUCT_IDEAS_MIN_REUSABILITY: float = 0.0

    # Email
    EMAIL_ENABLED: bool = False
    EMAIL_SMTP_HOST: str | None = None
    EMAIL_SMTP_PORT: int | None = None
    EMAIL_USERNAME: str | None = None
    EMAIL_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None
    EMAIL_TO: str | None = None

    # Telegram
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None


def _bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes", "on")


def load_config() -> Config:
    load_dotenv()

    with open('resources/config.yml', 'r') as file:
        config = yaml.safe_load(file)

    return Config(
        DATABASE_PATH=config["DATABASE_PATH"],
        FAISS_INDEX_PATH=config["FAISS_INDEX_PATH"],

        OLLAMA_BASE_URL=config["OLLAMA_BASE_URL"],
        OLLAMA_MODEL=config["OLLAMA_MODEL"],

        PERSONA_GENAI_NEWS_ENABLED=_bool(config["PERSONA_GENAI_NEWS_ENABLED"]),
        PERSONA_PRODUCT_IDEAS_ENABLED=_bool(config["PERSONA_PRODUCT_IDEAS_ENABLED"]),

        GENAI_NEWS_MIN_RELEVANCE=float(config["GENAI_NEWS_MIN_RELEVANCE"]),
        PRODUCT_IDEAS_MIN_REUSABILITY=float(config["PRODUCT_IDEAS_MIN_REUSABILITY"]),

        EMAIL_ENABLED=config["EMAIL_ENABLED"].lower() == "true",
        EMAIL_SMTP_HOST=config["EMAIL_SMTP_HOST"],
        EMAIL_SMTP_PORT=int(config["EMAIL_SMTP_PORT"]) or None,
        EMAIL_USERNAME=os.getenv("EMAIL_USERNAME"),
        EMAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
        EMAIL_FROM=config["EMAIL_FROM"],
        EMAIL_TO=config["EMAIL_TO"],

        TELEGRAM_ENABLED=config["FAISS_INDEX_PATH"].lower() == "true",
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
        TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID"),
    )

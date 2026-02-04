"""
Loads and handles config from config.yml
Email credentials (EMAIL_USERNAME, EMAIL_PASSWORD) are loaded from .env for security
"""
import os
from typing import List, Dict, Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class SourceConfig(BaseModel):
    """Configuration for a single ingestion source."""
    type: str  # reddit, rss, hackernews, producthunt
    enabled: bool = True
    subreddit: Optional[str] = None  # For reddit
    name: Optional[str] = None  # For rss
    feeds: Optional[List[str]] = None  # For rss


class IngestionConfig(BaseModel):
    """Configuration for a persona's ingestion pipeline."""
    sources: List[SourceConfig] = []
    keywords: List[str] = []
    min_engagement: int = 5
    top_k: int = 5  # Number of top digests to select


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
    EMAIL_SMTP_HOST: Optional[str] = None
    EMAIL_SMTP_PORT: Optional[int] = None
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    EMAIL_TO: Optional[str] = None

    # Telegram
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Ingestion configurations
    ingestion_genai_news: Optional[IngestionConfig] = None
    ingestion_product_ideas: Optional[IngestionConfig] = None


def _bool(value: str | bool) -> bool:
    """Convert string or bool to boolean."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def _get_config_path() -> str:
    """Get the path to config.yml, handling different working directories."""
    # Try relative path first
    if os.path.exists('resources/config.yml'):
        return 'resources/config.yml'

    # Try from project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(project_root, 'resources', 'config.yml')
    if os.path.exists(config_path):
        return config_path

    raise FileNotFoundError("Cannot find resources/config.yml")


def _parse_ingestion_config(data: Dict[str, Any]) -> IngestionConfig:
    """Parse ingestion configuration from YAML data."""
    sources = []
    for src in data.get("sources", []):
        sources.append(SourceConfig(
            type=src.get("type", ""),
            enabled=src.get("enabled", True),
            subreddit=src.get("subreddit"),
            name=src.get("name"),
            feeds=src.get("feeds"),
        ))

    return IngestionConfig(
        sources=sources,
        keywords=data.get("keywords", []),
        min_engagement=data.get("min_engagement", 5),
        top_k=data.get("top_k", 5),
    )


def load_config() -> Config:
    """Load configuration from config.yml and email credentials from .env."""
    # Load .env for sensitive credentials
    load_dotenv()

    config_path = _get_config_path()

    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    # Parse ingestion configurations
    ingestion = config.get("ingestion", {})
    ingestion_genai_news = None
    ingestion_product_ideas = None

    if "genai_news" in ingestion:
        ingestion_genai_news = _parse_ingestion_config(ingestion["genai_news"])

    if "product_ideas" in ingestion:
        ingestion_product_ideas = _parse_ingestion_config(ingestion["product_ideas"])

    return Config(
        DATABASE_PATH=config.get("DATABASE_PATH", "data/app.db"),
        FAISS_INDEX_PATH=config.get("FAISS_INDEX_PATH", "data/faiss.index"),

        OLLAMA_BASE_URL=config.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        OLLAMA_MODEL=config.get("OLLAMA_MODEL", "llama3.1:8b"),

        PERSONA_GENAI_NEWS_ENABLED=_bool(config.get("PERSONA_GENAI_NEWS_ENABLED", False)),
        PERSONA_PRODUCT_IDEAS_ENABLED=_bool(config.get("PERSONA_PRODUCT_IDEAS_ENABLED", False)),

        GENAI_NEWS_MIN_RELEVANCE=float(config.get("GENAI_NEWS_MIN_RELEVANCE", 0.4)),
        PRODUCT_IDEAS_MIN_REUSABILITY=float(config.get("PRODUCT_IDEAS_MIN_REUSABILITY", 0.5)),

        EMAIL_ENABLED=_bool(config.get("EMAIL_ENABLED", False)),
        EMAIL_SMTP_HOST=config.get("EMAIL_SMTP_HOST"),
        EMAIL_SMTP_PORT=int(config.get("EMAIL_SMTP_PORT", 587)) if config.get("EMAIL_SMTP_PORT") else None,
        EMAIL_USERNAME=os.getenv("EMAIL_USERNAME"),
        EMAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
        EMAIL_FROM=config.get("EMAIL_FROM"),
        EMAIL_TO=config.get("EMAIL_TO"),

        TELEGRAM_ENABLED=_bool(config.get("TELEGRAM_ENABLED", False)),
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
        TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID"),

        ingestion_genai_news=ingestion_genai_news,
        ingestion_product_ideas=ingestion_product_ideas,
    )


def get_enabled_sources(ingestion_config: IngestionConfig) -> List[SourceConfig]:
    """Get only enabled sources from an ingestion config."""
    return [src for src in ingestion_config.sources if src.enabled]

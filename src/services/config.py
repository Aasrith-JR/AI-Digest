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


class PipelineConfig(BaseModel):
    """
    Complete configuration for a single pipeline.
    Defines everything needed to run a digest pipeline.
    """
    name: str  # Unique pipeline name
    enabled: bool = True
    persona_name: str  # Reference to persona in ALL_PERSONAS
    ingestion: IngestionConfig
    fetch_hours: int = 24
    default_audience: str = "developer"
    score_field: str = "relevance_score"  # Field name in evaluation for scoring
    why_it_matters_field: Any = "why_it_matters"  # Field(s) to use for why_it_matters
    why_it_matters_fallback: str = "Relevant update."

    # Resolved at runtime
    _persona: Any = None

    @property
    def persona(self):
        """Lazy-load the Persona object from ALL_PERSONAS."""
        if self._persona is None:
            from core.personas import ALL_PERSONAS
            if self.persona_name not in ALL_PERSONAS:
                raise ValueError(f"Unknown persona: {self.persona_name}")
            self._persona = ALL_PERSONAS[self.persona_name]
        return self._persona

    class Config:
        # Allow private attributes
        underscore_attrs_are_private = True


class EmailColorsConfig(BaseModel):
    """Configuration for email template colors."""
    primary: str = "#6366f1"
    primary_dark: str = "#4f46e5"
    secondary: str = "#10b981"
    background: str = "#f8fafc"
    card_bg: str = "#ffffff"
    text_primary: str = "#1e293b"
    text_secondary: str = "#64748b"
    border: str = "#e2e8f0"
    accent: str = "#f59e0b"
    why_it_matters_bg: str = "#fef3c7"
    why_it_matters_text: str = "#92400e"


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
    email_colors: EmailColorsConfig = EmailColorsConfig()

    # Telegram
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Ingestion configurations (legacy - for backwards compatibility)
    ingestion_genai_news: Optional[IngestionConfig] = None
    ingestion_product_ideas: Optional[IngestionConfig] = None

    # New modular pipeline configurations
    pipelines: List[PipelineConfig] = []


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


def _parse_pipeline_config(name: str, data: Dict[str, Any]) -> PipelineConfig:
    """Parse a single pipeline configuration from YAML data."""
    ingestion_data = data.get("ingestion", {})
    ingestion = _parse_ingestion_config(ingestion_data)

    return PipelineConfig(
        name=name,
        enabled=_bool(data.get("enabled", True)),
        persona_name=data.get("persona", name.upper()),
        ingestion=ingestion,
        fetch_hours=data.get("fetch_hours", 24),
        default_audience=data.get("default_audience", "developer"),
        score_field=data.get("score_field", "relevance_score"),
        why_it_matters_field=data.get("why_it_matters_field", "why_it_matters"),
        why_it_matters_fallback=data.get("why_it_matters_fallback", "Relevant update."),
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

    # Parse new modular pipelines configuration
    pipelines = []
    pipelines_config = config.get("pipelines", {})
    for pipeline_name, pipeline_data in pipelines_config.items():
        try:
            pipeline_config = _parse_pipeline_config(pipeline_name, pipeline_data)
            pipelines.append(pipeline_config)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to parse pipeline '{pipeline_name}': {e}")

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
        email_colors=EmailColorsConfig(**config.get("email_colors", {})),

        TELEGRAM_ENABLED=_bool(config.get("TELEGRAM_ENABLED", False)),
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
        TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID"),

        ingestion_genai_news=ingestion_genai_news,
        ingestion_product_ideas=ingestion_product_ideas,
        pipelines=pipelines,
    )


def get_enabled_sources(ingestion_config: IngestionConfig) -> List[SourceConfig]:
    """Get only enabled sources from an ingestion config."""
    return [src for src in ingestion_config.sources if src.enabled]

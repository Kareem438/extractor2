"""
CHUNK-001: Configuration Management

Centralized configuration loading from environment variables and .env file.
Provides type-safe access to all system configuration parameters.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.

    Loads configuration from environment variables and .env file.
    Provides validation and default values for all settings.
    """

    # Database Configuration
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection URL"
    )
    DB_POOL_SIZE: int = Field(
        default=10,
        description="Database connection pool size"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=20,
        description="Maximum overflow connections beyond pool size"
    )

    # Server Configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    PORT: int = Field(
        default=7777,
        description="Server port"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    LOG_FILE: str = Field(
        default="./logs/app.log",
        description="Log file path"
    )

    # Vector Database Configuration
    CHROMA_PERSIST_DIR: str = Field(
        default="./chroma_db",
        description="ChromaDB persistence directory"
    )

    # External Tool Paths
    TESSERACT_PATH: str = Field(
        ...,
        description="Path to Tesseract OCR executable"
    )
    MODEL_CACHE_DIR: str = Field(
        ...,
        description="Directory for caching ML models"
    )

    # Processing Configuration
    CHECKPOINT_FREQUENCY: int = Field(
        default=50,
        description="Number of pages between processing checkpoints"
    )
    BATCH_INSERT_SIZE: int = Field(
        default=50,
        description="Batch size for database inserts"
    )

    # Image Processing Settings
    IMAGE_MAX_WIDTH: int = Field(
        default=800,
        description="Maximum image width in pixels"
    )
    IMAGE_MAX_HEIGHT: int = Field(
        default=600,
        description="Maximum image height in pixels"
    )

    # Anthropic API (Claude Vision for diagram analysis)
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key for Claude Vision (optional)"
    )

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = True


# Singleton settings instance
settings = Settings()

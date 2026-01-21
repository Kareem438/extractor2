"""
Worker Configuration

Configuration settings for the worker process.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class WorkerConfig(BaseSettings):
    """Worker configuration settings"""

    # Worker Identity
    worker_id: str = Field(default="worker-001", description="Unique worker identifier")

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")

    # Claude API
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    default_claude_model: str = Field(default="claude-sonnet-4-20250514", description="Default Claude model")

    # Polling Configuration
    poll_interval_seconds: int = Field(default=5, description="Seconds between task queue polls")
    heartbeat_interval_seconds: int = Field(default=10, description="Seconds between heartbeat updates")

    # Parallelism
    max_parallel_tasks: int = Field(default=3, description="Maximum tasks to process in parallel")

    # Rate Limiting
    rate_limit_check_interval_seconds: int = Field(default=60, description="Seconds between rate limit checks")
    rate_limit_backoff_seconds: int = Field(default=300, description="Initial backoff when rate limited")

    # Retry Configuration
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts per task")
    retry_delay_seconds: int = Field(default=30, description="Delay between retry attempts")

    # ChromaDB
    chroma_host: str = Field(default="localhost", description="ChromaDB host")
    chroma_port: int = Field(default=8000, description="ChromaDB port")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path (None for stdout)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global config instance
config: Optional[WorkerConfig] = None


def get_config() -> WorkerConfig:
    """Get or create worker configuration"""
    global config
    if config is None:
        config = WorkerConfig()
    return config

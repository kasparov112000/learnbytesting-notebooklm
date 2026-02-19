"""Configuration for NotebookLM Microservice."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 3034

    # Tailscale Configuration
    tailscale_ip: Optional[str] = None

    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "notebooklm"

    # Service URLs
    chess_ai_url: str = "http://localhost:3020"
    orchestrator_url: str = "http://localhost:8080"

    # Environment
    env_name: str = "LOCAL"

    # Logging
    log_level: str = "INFO"

    # LearnByTesting.ai dedicated notebook
    # This notebook contains all context about the LBT platform
    lbt_notebook_id: str = "21c5377f-c88a-408d-9bd0-d776ac26f0af"
    lbt_notebook_name: str = "LearnByTesting.ai Context"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

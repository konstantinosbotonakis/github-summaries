"""
Application configuration module.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


def load_database_config() -> Dict[str, Any]:
    """Load database configuration from database.json file."""
    config_path = Path("database.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("database", {})
        except (json.JSONDecodeError, IOError):
            # If config file is invalid, return empty dict to fall back to defaults
            pass
    return {"type": "sqlite", "path": "./test.db"}


class Settings(BaseSettings):
    """Application settings."""
    
    def __init__(self, **kwargs):
        # Call parent constructor first for Pydantic v2 compatibility
        super().__init__(**kwargs)
        # Load database config from file after initialization
        self._db_config = load_database_config()
    
    # Application Configuration
    APP_NAME: str = Field(default="GitHub Repository Monitor", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    DEBUG: bool = Field(default=True, env="DEBUG")
    SECRET_KEY: str = Field(default="your_secret_key_here_change_in_production", env="SECRET_KEY")
    
    # API Configuration
    API_V1_STR: str = Field(default="/api/v1", env="API_V1_STR")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Database Configuration - defaults to SQLite
    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        
        # Default to SQLite if no DATABASE_URL is provided
        db_path = self._db_config.get("path", "./test.db")
        return f"sqlite:///{db_path}"
    
    # GitHub API Configuration
    GITHUB_TOKEN: str = Field(default="", env="GITHUB_TOKEN")
    GITHUB_API_URL: str = Field(default="https://api.github.com", env="GITHUB_API_URL")
    
    # Hugging Face Model Configuration
    HF_MODEL_NAME: str = Field(default="google/flan-t5-base", env="HF_MODEL_NAME")
    HF_DEVICE: str = Field(default="cpu", env="HF_DEVICE")  # "cpu" or "cuda"
    HF_MAX_LENGTH: int = Field(default=512, env="HF_MAX_LENGTH")
    HF_CACHE_DIR: str = Field(default="./models", env="HF_CACHE_DIR")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring Configuration
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    TIMEOUT_SECONDS: int = Field(default=10, env="TIMEOUT_SECONDS")
    
    # Application Settings
    MAX_REPOSITORIES: int = Field(default=100, env="MAX_REPOSITORIES")
    SUMMARY_BATCH_SIZE: int = Field(default=10, env="SUMMARY_BATCH_SIZE")
    CACHE_EXPIRY_HOURS: int = Field(default=24, env="CACHE_EXPIRY_HOURS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields to be ignored


# Create settings instance
settings = Settings()


def get_database_url() -> str:
    """Get the database URL for SQLAlchemy."""
    return settings.DATABASE_URL


def get_hf_model_name() -> str:
    """Get the Hugging Face model name."""
    return settings.HF_MODEL_NAME


def get_hf_device() -> str:
    """Get the Hugging Face device."""
    return settings.HF_DEVICE


def get_hf_cache_dir() -> str:
    """Get the Hugging Face cache directory."""
    return settings.HF_CACHE_DIR


def is_development() -> bool:
    """Check if running in development mode."""
    return settings.DEBUG


def get_cors_origins() -> List[str]:
    """Get CORS origins."""
    if isinstance(settings.CORS_ORIGINS, str):
        return [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    return settings.CORS_ORIGINS
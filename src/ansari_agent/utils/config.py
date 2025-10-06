"""Configuration management for Ansari Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration."""

    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    KALIMAT_API_KEY = os.getenv("KALIMAT_API_KEY")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # API Endpoints
    KALEMAT_BASE_URL = "https://api.kalimat.dev/search"

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []

        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set")
        if not cls.KALIMAT_API_KEY:
            errors.append("KALIMAT_API_KEY is not set")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Singleton instance
config = Config()

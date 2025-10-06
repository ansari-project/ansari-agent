"""Configuration and environment variable management."""

import os
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration."""

    # Model IDs
    MODELS: Dict[str, str] = {
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "claude-opus-4-20250514": "Claude Opus 4.1",
        "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    }

    # Fairness configuration
    TEMPERATURE = 0.0
    MAX_TOKENS = 65536  # Updated to 65536 for all models
    SYSTEM_PROMPT: str | None = None

    # Session management
    SESSION_TTL_SECONDS = 900  # 15 minutes
    MAX_SESSIONS = 50
    MAX_HISTORY_TURNS = 10
    MAX_HISTORY_TOKENS = 8000

    # SSE configuration
    HEARTBEAT_INTERVAL_SECONDS = 10
    STREAM_TIMEOUT_SECONDS = 90  # Increased to allow multi-turn agent loops

    # API keys
    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key from environment."""
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is required"
            )
        return key

    @property
    def google_api_key(self) -> str:
        """Get Google API key from environment."""
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY environment variable is required")
        return key

    # Auth (optional - disable by not setting AUTH_PASSWORD)
    @property
    def auth_username(self) -> str:
        """Get auth username from environment (default: admin)."""
        return os.getenv("MODEL_COMPARISON_AUTH_USERNAME", "admin")

    @property
    def auth_password(self) -> str | None:
        """Get auth password from environment (None = auth disabled)."""
        return os.getenv("MODEL_COMPARISON_AUTH_PASSWORD")

    @property
    def auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self.auth_password is not None and len(self.auth_password) > 0

    def validate(self) -> None:
        """Validate configuration at startup."""
        # Trigger property access to validate keys exist
        _ = self.anthropic_api_key
        _ = self.google_api_key


# Global config instance
config = Config()

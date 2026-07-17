"""
Tour-resQ Configuration
Environment variables and app settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # --- App ---
    APP_NAME: str = "Tour-resQ"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # --- AI / LLM ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tour_resq.db")

    # --- SOS Dispatch ---
    SOS_WEBHOOK_URL: str = os.getenv("SOS_WEBHOOK_URL", "")
    TOURISM_HOTLINE: str = os.getenv("TOURISM_HOTLINE", "1900-6068")
    POLICE_HOTLINE: str = os.getenv("POLICE_HOTLINE", "113")
    TOURIST_POLICE_HOTLINE: str = os.getenv("TOURIST_POLICE_HOTLINE", "0243-942-8828")

    # --- Supported Languages ---
    # Priority markets as stated in the challenge brief
    SUPPORTED_LANGUAGES: list = ["en", "ko", "zh", "ru"]
    DEFAULT_LANGUAGE: str = "en"

    # --- Price Check Thresholds ---
    # z-score thresholds for 3-tier alert system
    PRICE_TIER_GREEN: float = 1.0    # Within 1 std dev = fair
    PRICE_TIER_YELLOW: float = 2.0   # 1-2 std dev = slightly above average
    PRICE_TIER_RED: float = 2.0      # > 2 std dev = significantly overpriced

    # Minimum sample size before making a verdict
    MIN_SAMPLE_SIZE: int = 5
    # Confidence threshold below which we say "insufficient data"
    MIN_CONFIDENCE: float = 0.6

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5500"
    ).split(",")

    @property
    def gemini_key(self) -> str:
        """Get the best available Gemini key."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY


settings = Settings()

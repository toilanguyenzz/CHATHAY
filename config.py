"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Gemini AI (support multi-key rotation for quota multiplication)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY_2: str = os.getenv("GEMINI_API_KEY_2", "")
    GEMINI_API_KEY_3: str = os.getenv("GEMINI_API_KEY_3", "")

    # FPT.AI TTS
    FPT_AI_API_KEY: str = os.getenv("FPT_AI_API_KEY", "")
    FPT_AI_VOICE: str = os.getenv("FPT_AI_VOICE", "banmai")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Limits
    FREE_DAILY_LIMIT: int = int(os.getenv("FREE_DAILY_LIMIT", "5"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "20"))

    # Paths
    TEMP_DIR: str = os.path.join(os.path.dirname(__file__), "temp")
    AUDIO_DIR: str = os.path.join(os.path.dirname(__file__), "temp", "audio")

    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories."""
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.AUDIO_DIR, exist_ok=True)


config = Config()
config.ensure_dirs()

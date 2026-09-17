from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings validated against .env file or environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot Token from @BotFather
    BOT_TOKEN: SecretStr = Field(
        ...,
        description="Telegram bot token obtained from @BotFather"
    )

    # Google Gemini API Settings (from Google AI Studio: aistudio.google.com)
    GEMINI_API_KEY: SecretStr = Field(
        ...,
        description="Google Gemini API key"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.6-flash",
        description="Gemini model: gemini-3.6-flash"
    )

    # Apiframe.ai Suno Music Gateway
    APIFRAME_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        description="Apiframe.ai API key (starts with afk_...)"
    )
    APIFRAME_BASE_URL: str = Field(
        default="https://api.apiframe.ai",
        description="Apiframe base URL"
    )

    # Mock Mode for Testing (avoids spending credits)
    USE_MOCK_MUSIC: bool = Field(
        default=False,
        description="If True, mocks Suno audio generation with delay and test mp3"
    )
    MOCK_AUDIO_URL: str = Field(
        default="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        description="Sample MP3 URL returned in mock mode"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached Settings instance.
    """
    return Settings()

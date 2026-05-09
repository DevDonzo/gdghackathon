from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env.local", ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    node_env: str = Field(default="development", alias="NODE_ENV")
    mongodb_uri: str = Field(alias="MONGODB_URI")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str | None = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    twilio_verify_orig_numbers: str | None = Field(default=None, alias="TWILIO_VERIFY_ORIG_NUMBERS")
    twilio_sandbox_to_number: str | None = Field(default=None, alias="TWILIO_SANDBOX_TO_NUMBER")
    public_base_url: str | None = Field(default=None, alias="PUBLIC_BASE_URL")
    frontend_base_url: str = Field(default="http://127.0.0.1:3000", alias="FRONTEND_BASE_URL")
    next_public_api_base_url: str = Field(default="http://127.0.0.1:8000", alias="NEXT_PUBLIC_API_BASE_URL")

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_phone_number)

    @property
    def twilio_verified_numbers(self) -> list[str]:
        if not self.twilio_verify_orig_numbers:
            return []
        return [item.strip() for item in self.twilio_verify_orig_numbers.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

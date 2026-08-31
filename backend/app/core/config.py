import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    recoveriq_mode: Literal["shadow", "assisted", "autonomous"] = "shadow"
    recoveriq_execute_razorpay_actions: bool = False
    recoveriq_autonomous_limit_paise: int = 1_000_000
    recoveriq_database_path: str = (
        "/tmp/recoveriq.sqlite3"
        if os.getenv("VERCEL")
        else "data/recoveriq.sqlite3"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def razorpay_api_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.razorpay_webhook_secret)

    @property
    def database_backend(self) -> Literal["postgresql", "sqlite"]:
        return "postgresql" if self.database_url else "sqlite"

    @property
    def durable_database_configured(self) -> bool:
        return bool(self.database_url) or not bool(os.getenv("VERCEL"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

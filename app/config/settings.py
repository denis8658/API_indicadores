import os
from typing import List

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "pocket-option-market-intelligence"
    api_base_url: str = "https://pocketoptionapi-mainscalp-production-0434.up.railway.app"
    log_level: str = "INFO"
    cache_ttl_seconds: int = 30
    max_candles: int = 500
    database_path: str = "market_intelligence.db"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    allowed_origins: str = "*"
    pocket_ssid: str = Field(default="", validation_alias=AliasChoices("POCKET_SSID", "POCKET_OPTION_SSID"))

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()

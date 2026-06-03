from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    ai_provider: str = "mock"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    cors_origins: tuple[str, ...] = ("*",)
    database_url: str = ""
    database_pool_recycle: int = 3600


def load_settings() -> Settings:
    load_dotenv(encoding="utf-8-sig")
    origins = os.getenv("BACKEND_CORS_ORIGINS", "*")
    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "mock").strip().lower() or "mock",
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()) or ("*",),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        database_pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "3600") or "3600"),
    )

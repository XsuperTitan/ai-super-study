from __future__ import annotations

from app.adapters.base import ModelAdapter
from app.adapters.deepseek import DeepSeekAdapter
from app.adapters.mock import MockModelAdapter
from app.config import Settings
from app.errors import ModelAdapterError


def create_adapter(settings: Settings) -> ModelAdapter:
    if settings.ai_provider == "deepseek":
        try:
            return DeepSeekAdapter(settings)
        except ModelAdapterError:
            return MockModelAdapter()
    return MockModelAdapter()

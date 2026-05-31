from __future__ import annotations

from dataclasses import dataclass

from app.adapters.base import ModelAdapter
from app.adapters.deepseek import DeepSeekAdapter
from app.adapters.mock import MockModelAdapter
from app.config import Settings
from app.errors import ModelAdapterError


@dataclass(frozen=True)
class AdapterSelection:
    adapter: ModelAdapter
    provider: str
    fallback_reason: str = ""


def create_adapter(settings: Settings) -> AdapterSelection:
    if settings.ai_provider == "deepseek":
        try:
            adapter = DeepSeekAdapter(settings)
            return AdapterSelection(adapter=adapter, provider=adapter.provider_name)
        except ModelAdapterError as exc:
            adapter = MockModelAdapter()
            return AdapterSelection(adapter=adapter, provider=adapter.provider_name, fallback_reason=str(exc))
    adapter = MockModelAdapter()
    reason = f"AI_PROVIDER={settings.ai_provider or 'mock'}"
    return AdapterSelection(adapter=adapter, provider=adapter.provider_name, fallback_reason=reason)

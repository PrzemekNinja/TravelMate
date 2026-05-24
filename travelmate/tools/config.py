from __future__ import annotations

import os
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LM_STUDIO = "lmstudio"


class ModelConfig(BaseModel):
    provider: ModelProvider = ModelProvider.OPENAI
    temperature: float = 0.3

    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-latest"
    google_model: str = "gemini-1.5-pro"
    lmstudio_model: str = "local-model"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_api_key: str = "lm-studio"

    here_api_key: str | None = None
    here_base_url: str = "https://geocode.search.hereapi.com/v1"
    here_geocode_base_url: str = "https://geocode.search.hereapi.com/v1"
    here_search_base_url: str = "https://discover.search.hereapi.com/v1"

    tripadvisor_api_key: str | None = None
    tripadvisor_base_url: str = "https://api.content.tripadvisor.com/api/v1"
    tripadvisor_language: str = "en"
    tripadvisor_currency: str = "USD"


def load_model_config() -> ModelConfig:
    load_dotenv()

    provider_raw = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
    provider = ModelProvider(provider_raw)

    here_base_url = os.getenv("HERE_BASE_URL", "https://geocode.search.hereapi.com/v1")
    here_geocode_base_url = os.getenv("HERE_GEOCODE_BASE_URL", "").strip()
    here_search_base_url = os.getenv("HERE_SEARCH_BASE_URL", "").strip()

    if not here_geocode_base_url:
        if "geocode.search.hereapi.com" in here_base_url:
            here_geocode_base_url = here_base_url
        else:
            here_geocode_base_url = "https://geocode.search.hereapi.com/v1"

    if not here_search_base_url:
        if "discover.search.hereapi.com" in here_base_url:
            here_search_base_url = here_base_url
        else:
            here_search_base_url = "https://discover.search.hereapi.com/v1"

    return ModelConfig(
        provider=provider,
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.3")),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        google_model=os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
        lmstudio_model=os.getenv("LMSTUDIO_MODEL", "local-model"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        lmstudio_api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        here_api_key=os.getenv("HERE_API_KEY"),
        here_base_url=here_base_url,
        here_geocode_base_url=here_geocode_base_url,
        here_search_base_url=here_search_base_url,
        tripadvisor_api_key=os.getenv("TRIPADVISOR_API_KEY"),
        tripadvisor_base_url=os.getenv("TRIPADVISOR_BASE_URL", "https://api.content.tripadvisor.com/api/v1"),
        tripadvisor_language=os.getenv("TRIPADVISOR_LANGUAGE", "en"),
        tripadvisor_currency=os.getenv("TRIPADVISOR_CURRENCY", "USD"),
    )

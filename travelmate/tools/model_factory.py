from __future__ import annotations

import importlib
from urllib import error, request

from langchain_openai import ChatOpenAI

from .config import ModelProvider, load_model_config


class ModelConfigurationError(RuntimeError):
    """Raised when model provider config is invalid or incomplete."""


def _require(value: str | None, env_name: str) -> str:
    if value and value.strip() and not value.startswith("your_"):
        return value
    raise ModelConfigurationError(f"Brak poprawnej wartości zmiennej: {env_name}")


def _active_model_name() -> str:
    cfg = load_model_config()

    if cfg.provider == ModelProvider.OPENAI:
        return cfg.openai_model
    if cfg.provider == ModelProvider.ANTHROPIC:
        return cfg.anthropic_model
    if cfg.provider == ModelProvider.GOOGLE:
        return cfg.google_model
    if cfg.provider == ModelProvider.LM_STUDIO:
        return cfg.lmstudio_model

    raise ModelConfigurationError(f"Nieobsługiwany provider: {cfg.provider}")


def get_model_runtime_status() -> tuple[str, str, bool, str]:
    """Return provider, model name, active flag and short diagnostic message."""
    cfg = load_model_config()
    provider = cfg.provider.value
    model_name = _active_model_name()

    try:
        _ = get_chat_model()

        if cfg.provider == ModelProvider.LM_STUDIO:
            models_url = f"{cfg.lmstudio_base_url.rstrip('/')}/models"
            with request.urlopen(models_url, timeout=1.5) as response:
                if response.status < 200 or response.status >= 300:
                    raise ModelConfigurationError(
                        f"LM Studio zwrócił status HTTP {response.status}"
                    )

        return provider, model_name, True, "Połączenie wygląda poprawnie."
    except (ModelConfigurationError, error.URLError, TimeoutError, ValueError) as exc:
        return provider, model_name, False, str(exc)
    except Exception as exc:
        return provider, model_name, False, str(exc)


def get_chat_model():
    cfg = load_model_config()

    if cfg.provider == ModelProvider.OPENAI:
        return ChatOpenAI(
            model=cfg.openai_model,
            api_key=_require(cfg.openai_api_key, "OPENAI_API_KEY"),
            temperature=cfg.temperature,
        )

    if cfg.provider == ModelProvider.ANTHROPIC:
        module = importlib.import_module("langchain_anthropic")
        ChatAnthropic = getattr(module, "ChatAnthropic")

        return ChatAnthropic(
            model=cfg.anthropic_model,
            api_key=_require(cfg.anthropic_api_key, "ANTHROPIC_API_KEY"),
            temperature=cfg.temperature,
        )

    if cfg.provider == ModelProvider.GOOGLE:
        module = importlib.import_module("langchain_google_genai")
        ChatGoogleGenerativeAI = getattr(module, "ChatGoogleGenerativeAI")

        return ChatGoogleGenerativeAI(
            model=cfg.google_model,
            google_api_key=_require(cfg.google_api_key, "GOOGLE_API_KEY"),
            temperature=cfg.temperature,
        )

    if cfg.provider == ModelProvider.LM_STUDIO:
        return ChatOpenAI(
            model=cfg.lmstudio_model,
            api_key=cfg.lmstudio_api_key,
            base_url=cfg.lmstudio_base_url,
            temperature=cfg.temperature,
        )

    raise ModelConfigurationError(f"Nieobsługiwany provider: {cfg.provider}")

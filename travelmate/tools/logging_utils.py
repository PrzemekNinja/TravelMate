from __future__ import annotations

import logging


LOG_NAMESPACE = "travelmate"


class AgentNameFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        name = record.name
        if name.startswith(f"{LOG_NAMESPACE}."):
            name = name[len(LOG_NAMESPACE) + 1 :]
        record.agent_name = name  # type: ignore[attr-defined]
        return super().format(record)


def compact_text(value: str, max_len: int = 180) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "…"


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger used across TravelMate modules."""
    return logging.getLogger(f"{LOG_NAMESPACE}.{name}")


def get_travelmate_logger() -> logging.Logger:
    logger = logging.getLogger(LOG_NAMESPACE)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

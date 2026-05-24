from __future__ import annotations

from typing import Any


def _dict_text(block: dict[str, Any]) -> str:
    """Extract a text fragment from a single structured content block."""
    text = block.get("text")
    if isinstance(text, str):
        return text

    if isinstance(text, dict):
        value = text.get("value")
        if isinstance(value, str):
            return value

    content = block.get("content")
    if isinstance(content, str):
        return content

    return ""


def content_to_text(content: Any) -> str:
    """Normalize LangChain message content (str | list[blocks]) into plain text."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(_dict_text(item))
            elif item is not None:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()

    if content is None:
        return ""

    return str(content).strip()


def message_to_text(message: Any) -> str:
    """Extract text from a model response object or raw content."""
    raw_content = getattr(message, "content", message)
    return content_to_text(raw_content)

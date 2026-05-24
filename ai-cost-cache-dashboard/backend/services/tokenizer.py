"""Token counting service using tiktoken (cl100k_base encoding)."""
from __future__ import annotations

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a text string using cl100k_base encoding."""
    return len(_ENCODING.encode(text))


def count_tokens_pair(request_text: str, response_text: str) -> dict:
    """Count input and output tokens and return a summary dict."""
    input_tokens = count_tokens(request_text)
    output_tokens = count_tokens(response_text)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }

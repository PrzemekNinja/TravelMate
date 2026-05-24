"""
Thread-safe token usage tracker for TravelMate pipeline.

Each agent calls record() after its LLM invoke. At the end of the pipeline,
planner_service calls get_summary() to retrieve the full breakdown.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTokenUsage:
    agent: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class PipelineTokenSummary:
    agents: list[AgentTokenUsage] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    model_name: str = ""
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "agents": [
                {
                    "agent": a.agent,
                    "input_tokens": a.input_tokens,
                    "output_tokens": a.output_tokens,
                    "total_tokens": a.total_tokens,
                }
                for a in self.agents
            ],
        }


class TokenTracker:
    """Singleton tracker — one instance per pipeline run."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agents: list[AgentTokenUsage] = []
        self._model_name: str = ""
        self._provider: str = ""

    def set_model_info(self, model_name: str, provider: str) -> None:
        with self._lock:
            self._model_name = model_name
            self._provider = provider

    def record(self, agent_name: str, response: Any) -> None:
        """Extract token counts from a LangChain response and record them."""
        input_tokens = 0
        output_tokens = 0

        # LangChain standard: response.usage_metadata
        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0

        # Fallback: response_metadata (OpenAI / Anthropic raw)
        if input_tokens == 0 and output_tokens == 0:
            meta = getattr(response, "response_metadata", {}) or {}
            token_usage = meta.get("token_usage") or meta.get("usage") or {}
            if isinstance(token_usage, dict):
                input_tokens = (
                    token_usage.get("prompt_tokens")
                    or token_usage.get("input_tokens")
                    or 0
                )
                output_tokens = (
                    token_usage.get("completion_tokens")
                    or token_usage.get("output_tokens")
                    or 0
                )

        with self._lock:
            self._agents.append(
                AgentTokenUsage(
                    agent=agent_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                )
            )

    def get_summary(self) -> PipelineTokenSummary:
        with self._lock:
            agents = list(self._agents)
            total_in = sum(a.input_tokens for a in agents)
            total_out = sum(a.output_tokens for a in agents)
            return PipelineTokenSummary(
                agents=agents,
                total_input_tokens=total_in,
                total_output_tokens=total_out,
                total_tokens=total_in + total_out,
                model_name=self._model_name,
                provider=self._provider,
            )

    def reset(self) -> None:
        with self._lock:
            self._agents = []
            self._model_name = ""
            self._provider = ""


# Module-level instance — reset at the start of each pipeline run
_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    return _tracker

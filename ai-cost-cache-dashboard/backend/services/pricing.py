"""Pricing table loader and cost calculator."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

_PRICING_PATH = Path(__file__).parent.parent / "data" / "pricing.json"


def load_pricing() -> dict:
    with open(_PRICING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_pricing_stale(last_updated_str: str, days: int = 30) -> bool:
    try:
        last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d").date()
        return (date.today() - last_updated).days > days
    except ValueError:
        return True


def compute_costs(input_tokens: int, output_tokens: int) -> dict:
    """Compute cost estimates for all models and return sorted results."""
    pricing = load_pricing()
    last_updated = pricing["last_updated"]
    stale = is_pricing_stale(last_updated)

    costs = []
    for model in pricing["models"]:
        input_cost = (input_tokens / 1_000_000) * model["input_price_per_million_usd"]
        output_cost = (output_tokens / 1_000_000) * model["output_price_per_million_usd"]
        total_cost = input_cost + output_cost
        costs.append({
            "provider": model["provider"],
            "model": model["model"],
            "model_id": model["model_id"],
            "color": model["color"],
            "input_price_per_million_usd": model["input_price_per_million_usd"],
            "output_price_per_million_usd": model["output_price_per_million_usd"],
            "input_cost_usd": round(input_cost, 8),
            "output_cost_usd": round(output_cost, 8),
            "total_cost_usd": round(total_cost, 8),
        })

    # Sort cheapest to most expensive
    costs.sort(key=lambda x: x["total_cost_usd"])

    # Add savings vs most expensive
    if costs:
        max_cost = costs[-1]["total_cost_usd"]
        for c in costs:
            if max_cost > 0:
                c["savings_vs_most_expensive_pct"] = round(
                    (1 - c["total_cost_usd"] / max_cost) * 100, 1
                )
            else:
                c["savings_vs_most_expensive_pct"] = 0.0

    return {
        "costs": costs,
        "pricing_last_updated": last_updated,
        "pricing_stale": stale,
    }

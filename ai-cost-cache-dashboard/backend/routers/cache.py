"""Semantic cache router."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.pricing import load_pricing
from services.semantic_cache import cache

router = APIRouter(prefix="/api/cache", tags=["cache"])


class AddEntryRequest(BaseModel):
    key: str
    response: str


class QueryRequest(BaseModel):
    query: str
    threshold: float = 0.85
    reference_model_id: str = "gpt-4o-mini"


def _get_output_price(model_id: str) -> float:
    pricing = load_pricing()
    for m in pricing["models"]:
        if m["model_id"] == model_id:
            return m["output_price_per_million_usd"]
    return 0.60  # default gpt-4o-mini


@router.get("/entries")
def get_entries():
    return {"entries": cache.get_entries()}


@router.post("/entries")
def add_entry(body: AddEntryRequest):
    if not body.key.strip():
        raise HTTPException(status_code=422, detail="key cannot be empty")
    if not body.response.strip():
        raise HTTPException(status_code=422, detail="response cannot be empty")
    entry = cache.add_entry(body.key, body.response)
    return {"entry": entry.to_dict()}


@router.post("/query")
def query_cache(body: QueryRequest):
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query cannot be empty")
    if not (0.0 <= body.threshold <= 1.0):
        raise HTTPException(status_code=422, detail="threshold must be between 0.0 and 1.0")

    output_price = _get_output_price(body.reference_model_id)
    result = cache.query(body.query, body.threshold, output_price)
    return result


@router.get("/stats")
def get_stats():
    return cache.get_stats()


@router.get("/history")
def get_history():
    return {"history": cache.get_history()}


@router.get("/savings-timeline")
def get_savings_timeline():
    return {"timeline": cache.get_savings_timeline()}

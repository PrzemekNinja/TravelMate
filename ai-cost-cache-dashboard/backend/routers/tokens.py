"""Token cost comparison router."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.pricing import compute_costs
from services.tokenizer import count_tokens_pair

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class AnalyzeRequest(BaseModel):
    request_text: str
    response_text: str


@router.post("/analyze")
def analyze_tokens(body: AnalyzeRequest):
    if not body.request_text.strip():
        raise HTTPException(status_code=422, detail="request_text cannot be empty")
    if not body.response_text.strip():
        raise HTTPException(status_code=422, detail="response_text cannot be empty")

    token_counts = count_tokens_pair(body.request_text, body.response_text)
    pricing_result = compute_costs(
        token_counts["input_tokens"],
        token_counts["output_tokens"],
    )

    return {
        **token_counts,
        **pricing_result,
    }

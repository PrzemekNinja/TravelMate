"""Semantic cache service with cosine similarity lookup."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

_SEED_PATH = Path(__file__).parent.parent / "data" / "cache_seed.json"
_DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Lazy-loaded sentence transformer model
_model = None


def _get_model():
    global _model
    if _model is None and not _DEMO_MODE:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _keyword_vector(text: str) -> np.ndarray:
    """
    Simple keyword-overlap embedding for demo mode.
    Builds a bag-of-words style vector over a fixed travel vocabulary,
    so semantically similar queries (e.g. 'Prague attractions' vs
    'top things to see in Prague') produce high cosine similarity.
    """
    VOCAB = [
        # cities
        "prague", "rome", "tokyo", "barcelona", "amsterdam", "paris", "london",
        "berlin", "vienna", "lisbon", "madrid", "budapest", "krakow", "warsaw",
        # topics
        "attraction", "attractions", "sights", "museum", "castle", "church",
        "transport", "metro", "bus", "tram", "train", "flight", "airport",
        "food", "eat", "restaurant", "cuisine", "beer", "wine", "coffee",
        "hotel", "hostel", "accommodation", "stay", "neighborhood", "area",
        "best", "top", "visit", "see", "do", "guide", "tips", "time",
        "spring", "summer", "autumn", "winter", "season", "weather",
        "budget", "cheap", "expensive", "cost", "price", "money",
        "walk", "bike", "cycle", "car", "taxi", "uber",
        "history", "culture", "art", "architecture", "park", "garden",
        "brewery", "pub", "bar", "nightlife", "market", "shopping",
        "day", "trip", "tour", "itinerary", "plan", "travel",
    ]
    text_lower = text.lower()
    # tokenise on non-alpha
    import re
    words = set(re.split(r'[^a-z]+', text_lower))
    vec = np.array([1.0 if w in words else 0.0 for w in VOCAB], dtype=np.float32)
    # add a small noise so zero-vectors don't collapse
    vec += np.random.default_rng(abs(hash(text)) % (2**32)).uniform(0, 0.05, len(VOCAB)).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def _embed(text: str) -> list[float]:
    """Generate embedding for text. Uses keyword-overlap in demo mode."""
    if _DEMO_MODE:
        return _keyword_vector(text).tolist()
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


@dataclass
class CacheEntry:
    id: str
    key: str
    response: str
    embedding: list[float]
    created_at: str
    hit_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "response": self.response,
            "response_preview": self.response[:120] + "..." if len(self.response) > 120 else self.response,
            "created_at": self.created_at,
            "hit_count": self.hit_count,
        }


@dataclass
class QueryHistoryItem:
    query: str
    hit: bool
    similarity: float
    matched_key: Optional[str]
    timestamp: str
    savings_usd: float = 0.0


class SemanticCache:
    def __init__(self):
        self._entries: dict[str, CacheEntry] = {}
        self._history: list[QueryHistoryItem] = []
        self._total_queries = 0
        self._total_hits = 0
        self._cumulative_savings = 0.0
        self._load_seed()

    def _load_seed(self):
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            seed_data = json.load(f)
        for item in seed_data:
            entry_id = str(uuid.uuid4())
            embedding = _embed(item["key"])
            entry = CacheEntry(
                id=entry_id,
                key=item["key"],
                response=item["response"],
                embedding=embedding,
                created_at=datetime.utcnow().isoformat(),
            )
            self._entries[entry_id] = entry

    def add_entry(self, key: str, response: str) -> CacheEntry:
        entry_id = str(uuid.uuid4())
        embedding = _embed(key)
        entry = CacheEntry(
            id=entry_id,
            key=key,
            response=response,
            embedding=embedding,
            created_at=datetime.utcnow().isoformat(),
        )
        self._entries[entry_id] = entry
        return entry

    def query(self, query_text: str, threshold: float = 0.85, reference_model_cost_per_output_token: float = 0.0) -> dict:
        query_embedding = _embed(query_text)
        best_similarity = -1.0
        best_entry: Optional[CacheEntry] = None
        second_best_similarity = -1.0
        second_best_entry: Optional[CacheEntry] = None

        for entry in self._entries.values():
            sim = _cosine_similarity(query_embedding, entry.embedding)
            if sim > best_similarity:
                second_best_similarity = best_similarity
                second_best_entry = best_entry
                best_similarity = sim
                best_entry = entry
            elif sim > second_best_similarity:
                second_best_similarity = sim
                second_best_entry = entry

        hit = best_similarity >= threshold and best_entry is not None
        self._total_queries += 1

        savings_usd = 0.0
        if hit and best_entry:
            best_entry.hit_count += 1
            self._total_hits += 1
            # Estimate savings: cost of generating the cached response from scratch
            from services.tokenizer import count_tokens
            output_tokens = count_tokens(best_entry.response)
            savings_usd = (output_tokens / 1_000_000) * reference_model_cost_per_output_token
            self._cumulative_savings += savings_usd

        history_item = QueryHistoryItem(
            query=query_text,
            hit=hit,
            similarity=round(best_similarity, 4),
            matched_key=best_entry.key if hit and best_entry else None,
            timestamp=datetime.utcnow().isoformat(),
            savings_usd=round(savings_usd, 8),
        )
        self._history.insert(0, history_item)
        if len(self._history) > 20:
            self._history = self._history[:20]

        result = {
            "hit": hit,
            "similarity": round(best_similarity, 4),
            "threshold": threshold,
        }

        if hit and best_entry:
            result["matched_entry"] = best_entry.to_dict()
            result["savings_usd"] = round(savings_usd, 8)
            result["closest_miss"] = None
        else:
            result["matched_entry"] = None
            result["savings_usd"] = 0.0
            if best_entry:
                result["closest_miss"] = {
                    "key": best_entry.key,
                    "similarity": round(best_similarity, 4),
                }
            else:
                result["closest_miss"] = None

        return result

    def get_entries(self) -> list[dict]:
        return [e.to_dict() for e in self._entries.values()]

    def get_stats(self) -> dict:
        hit_rate = (self._total_hits / self._total_queries * 100) if self._total_queries > 0 else 0.0
        return {
            "total_entries": len(self._entries),
            "total_queries": self._total_queries,
            "total_hits": self._total_hits,
            "total_misses": self._total_queries - self._total_hits,
            "hit_rate_pct": round(hit_rate, 1),
            "cumulative_savings_usd": round(self._cumulative_savings, 8),
        }

    def get_history(self) -> list[dict]:
        return [
            {
                "query": h.query,
                "hit": h.hit,
                "similarity": h.similarity,
                "matched_key": h.matched_key,
                "timestamp": h.timestamp,
                "savings_usd": h.savings_usd,
            }
            for h in self._history
        ]

    def get_savings_timeline(self) -> list[dict]:
        """Return cumulative savings over time for the chart."""
        timeline = []
        cumulative = 0.0
        for item in reversed(self._history):
            cumulative += item.savings_usd
            timeline.append({
                "timestamp": item.timestamp,
                "savings_usd": round(item.savings_usd, 8),
                "cumulative_savings_usd": round(cumulative, 8),
                "hit": item.hit,
            })
        return timeline


# Singleton instance
cache = SemanticCache()

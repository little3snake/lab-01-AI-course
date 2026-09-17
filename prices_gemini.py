"""Gemini pricing used by Part 3."""

from __future__ import annotations
from dataclasses import dataclass

PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
PRICE_CHECKED = "2026-09-17"

@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float

MODELS = {"gemini-3.6-flash": ModelPrice(input_per_million=0.75,output_per_million=3.75,),}
DEFAULT_MODEL = "gemini-3.6-flash"

def cost_usd(model_key: str, input_tokens: int, output_tokens: int,) -> float:
    """Return Standard paid-tier cost of one request in USD."""
    price = MODELS[model_key]

    return (input_tokens / 1_000_000 * price.input_per_million
            + output_tokens / 1_000_000 * price.output_per_million
    )
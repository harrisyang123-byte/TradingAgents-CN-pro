"""Deterministic 5-tier rating parser.

Extracts buy/sell/hold ratings from text without requiring an LLM call.
Supports the standard 5-tier rating system:
    Buy, Overweight, Hold, Underweight, Sell
"""

from typing import Optional
from enum import Enum


class Rating(str, Enum):
    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


_RATING_PATTERNS: list[tuple[str, Rating]] = [
    ("strong buy", Rating.BUY),
    ("buy", Rating.BUY),
    ("overweight", Rating.OVERWEIGHT),
    ("neutral", Rating.HOLD),
    ("hold", Rating.HOLD),
    ("underweight", Rating.UNDERWEIGHT),
    ("sell", Rating.SELL),
    ("strong sell", Rating.SELL),
]


def parse_rating(text: str) -> Optional[Rating]:
    """Extract a 5-tier rating from text.

    Searches the input text for known rating keywords (case-insensitive)
    and returns the first match. More specific patterns (e.g. "strong buy")
    are checked before generic ones.

    Args:
        text: The text to search for a rating.

    Returns:
        A Rating enum if found, or None if no rating is detected.
    """
    if not text:
        return None

    lower = text.lower()
    for pattern, rating in _RATING_PATTERNS:
        if pattern in lower:
            return rating
    return None

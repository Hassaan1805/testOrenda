from __future__ import annotations

import os
import time
from typing import Generator

from anthropic import Anthropic
from anthropic.types import MessageStreamEvent

from prompts import SYSTEM_INSTRUCTIONS


def _has_api_key() -> bool:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(api_key) and api_key != "your_api_key_here"


def _client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in environment")
    return Anthropic(api_key=api_key)


def _mock_reflection_stream(mood: str, journal_text: str) -> Generator[str, None, None]:
    """Deterministic fallback stream for local dev when no API key is configured."""

    entry_hint = (
        journal_text.strip()[:120] + ("…" if len(journal_text.strip()) > 120 else "")
        if journal_text.strip()
        else "your honest words"
    )

    blocks = [
        "SUMMARY: ",
        f"You shared a {mood.lower()} moment. {entry_hint} shows self-awareness and care.\n",
        "EMOTIONS: ",
        "Hopeful, Curious, Steady\n",
        "REFLECTION QUESTIONS: ",
        "1. What feeling wants a little more attention right now?\n",
        "2. What is one gentle step you can take after writing?\n",
        "ENCOURAGEMENT: ",
        "You showed up for yourself by writing. That alone is meaningful progress.\n",
        "SMALL GOAL: ",
        "Write one sentence you would offer a close friend in your situation.\n",
        "TODAY'S BLOOM: ",
        "Soft honesty grows into steady clarity.\n",
    ]

    for block in blocks:
        yield block
        time.sleep(0.05)


def stream_reflection_text(mood: str, journal_text: str) -> Generator[str, None, None]:
    """Streams plain-text reflection content from Claude.

    Yields small text chunks that the frontend can parse incrementally.
    Falls back to a mock stream when ANTHROPIC_API_KEY is not configured.
    """

    if not _has_api_key():
        yield from _mock_reflection_stream(mood, journal_text)
        return

    client = _client()

    user_prompt = (
        f"User mood: {mood}\n\n"
        "User journal entry:\n"
        f"{journal_text}\n\n"
        "Now produce the reflection in the required plain-text labeled format."
    )

    with client.messages.stream(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        max_tokens=600,
        system=SYSTEM_INSTRUCTIONS,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta
                if getattr(delta, "text", None):
                    yield delta.text
            elif event.type == "message_delta":
                continue
            else:
                continue


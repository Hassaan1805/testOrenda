from __future__ import annotations

import os
import time
from typing import Generator

from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import SYSTEM_INSTRUCTIONS

# Ensure GEMINI_API_KEY (and friends) are available when this module is imported
# directly, independent of import order in the FastAPI app.
load_dotenv()


class GeminiError(RuntimeError):
    """Raised when a Gemini request cannot be completed."""


def _model_name() -> str:
    """Return the configured Gemini Flash model (overridable via GEMINI_MODEL)."""
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _has_api_key() -> bool:
    api_key = os.getenv("GEMINI_API_KEY", "")
    return bool(api_key) and api_key != "your_api_key_here"


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("Missing GEMINI_API_KEY in environment")
    return genai.Client(api_key=api_key)


def _reflection_config() -> types.GenerateContentConfig:
    """Shared request config so streaming/non-streaming paths stay in sync."""
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTIONS,
        max_output_tokens=600,
    )


def generate_reflection(journal_text: str) -> str:
    """Generate a plain-text reflection for a journal entry (non-streaming).

    Reads the system prompt from :mod:`prompts`, sends ``journal_text`` to
    Gemini, and returns the model's plain-text response.

    Raises:
        GeminiError: if the API key is missing, the request fails, or the
            model returns an empty response.
    """
    if not _has_api_key():
        raise GeminiError("Missing GEMINI_API_KEY in environment")

    client = _client()

    try:
        response = client.models.generate_content(
            model=_model_name(),
            contents=journal_text,
            config=_reflection_config(),
        )
    except Exception as exc:  # SDK raises various provider-specific errors
        raise GeminiError(f"Gemini API request failed: {exc}") from exc

    text = response.text
    if not text:
        raise GeminiError("Gemini API returned an empty response")

    return text


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
    """Streams plain-text reflection content from Gemini.

    Yields small text chunks that the frontend can parse incrementally.
    Falls back to a mock stream when GEMINI_API_KEY is not configured.
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

    try:
        stream = client.models.generate_content_stream(
            model=_model_name(),
            contents=user_prompt,
            config=_reflection_config(),
        )

        for chunk in stream:
            if chunk.text:
                yield chunk.text
    except Exception as exc:  # SDK raises various provider-specific errors
        raise GeminiError(f"Gemini API request failed: {exc}") from exc

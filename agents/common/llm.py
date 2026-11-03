"""Ask the model to phrase numbers that core/ has already computed.

If the key is missing, the call fails, or the reply drops a required figure,
the deterministic fallback is what the room sees.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import httpx

from agents.common.settings import get_settings
from core.load import repo_root

logger = logging.getLogger(__name__)
Completer = Callable[..., str | None]


def phrase(
    *,
    agent: str,
    facts: dict,
    fallback: str,
    required: list[str],
    complete: Completer | None = None,
) -> str:
    text = (complete or complete_chat)(agent=agent, facts=facts, fallback=fallback)
    if not text:
        return fallback
    cleaned = text.strip()
    if any(piece not in cleaned for piece in required):
        logger.info("llm reply dropped a computed figure; using the fallback")
        return fallback
    return cleaned


def complete_chat(*, agent: str, facts: dict, fallback: str) -> str | None:
    settings = get_settings()
    if not settings.llm_api_key or not settings.llm_base_url:
        return None
    prompt_path = Path(repo_root()) / "prompts" / f"{agent}_agent.md"
    system = prompt_path.read_text() if prompt_path.exists() else "Write a short room message."
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps({"facts": facts, "fallback": fallback}, default=str),
            },
        ],
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("llm call failed")
        return None

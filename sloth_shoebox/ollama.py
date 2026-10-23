"""A minimal client for a local Ollama server. Nothing here talks to the internet."""

from __future__ import annotations

from typing import Any

import httpx


class OllamaError(RuntimeError):
    """The local model runtime is missing, slow, or returned something unusable."""


def chat(
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    images: list[str] | None = None,
    json_mode: bool = False,
    timeout: float = 90.0,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Send one chat request and return the assistant text.

    `images` are base64 strings attached to the last user message.
    `transport` lets tests swap in an in-process fake server.
    """
    if images:
        messages = [*messages[:-1], {**messages[-1], "images": images}]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0},
    }
    if json_mode:
        payload["format"] = "json"
    try:
        with httpx.Client(transport=transport, timeout=httpx.Timeout(timeout, connect=1.5)) as c:
            response = c.post(f"{base_url}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise OllamaError(str(exc) or exc.__class__.__name__) from exc
    text = str(content).strip()
    if not text:
        raise OllamaError("empty response")
    return text

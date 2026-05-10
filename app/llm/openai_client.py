import json
import os
from collections.abc import AsyncIterator

import httpx


def _require_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def plan_tool_call(system_prompt: str, user_text: str) -> dict:
    """Synchronous planner call (standalone scripts / tests). Prefer plan_tool_call_async in routes."""
    api_key = _require_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
        "max_tokens": 320,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON from planner") from exc
    return parsed


async def plan_tool_call_async(
    client: httpx.AsyncClient, system_prompt: str, user_text: str
) -> dict:
    """Planner call using the shared AsyncClient from app.state (dependency injection)."""
    api_key = _require_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
        "max_tokens": 320,
        "response_format": {"type": "json_object"},
    }
    response = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON from planner") from exc
    return parsed


async def stream_chat_completion_text(
    client: httpx.AsyncClient, payload: dict
) -> AsyncIterator[str]:
    """Yield assistant content deltas from OpenAI streaming chat completions."""
    api_key = _require_api_key()
    stream_body = {**payload, "stream": True}
    async with client.stream(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        json=stream_body,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                chunk = line[6:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta

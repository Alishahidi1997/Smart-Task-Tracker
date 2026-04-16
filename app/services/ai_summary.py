# daily blurb from completed tasks — real openai if key set, else fake text
import os

import httpx

from app.models import Task


def pick_mode():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return "openai", key
    return "mock", ""


def mock_summary(tasks: list[Task]) -> str:
    if not tasks:
        return "No completed tasks in the list yet. Mark a few as done and try again."

    titles = [t.title for t in tasks[:15]]
    joined = ", ".join(titles)
    n = len(tasks)
    return (
        f"You have {n} completed task(s) on file. Recent ones include: {joined}. "
        "Keep shipping — this is the mock summary (no API key set)."
    )


def openai_summary(tasks: list[Task], api_key: str) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    lines = []
    for t in tasks[:40]:
        lines.append(f"- {t.title} (id {t.id})")

    user_block = "Completed tasks:\n" + ("\n".join(lines) if lines else "(none)")

    messages = [
        {
            "role": "system",
            "content": "You write short daily productivity summaries. 2-4 sentences, friendly, no markdown.",
        },
        {"role": "user", "content": user_block + "\n\nWrite the daily summary."},
    ]

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.6,
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["choices"][0]["message"]["content"].strip()


def build_daily_summary(tasks: list[Task]) -> tuple[str, str]:
    mode, key = pick_mode()
    if mode == "mock":
        return mock_summary(tasks), "mock"
    return openai_summary(tasks, key), "openai"

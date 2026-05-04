"""Role-aware dashboard payloads built from the same task dataset (Day 22 roadmap)."""

from datetime import datetime, timezone

from app.services.category_guess import guess_category
from app.services.insights import (
    build_priority_suggestions,
    build_productivity_insights,
    build_weekly_retro,
)


def _status_counts(tasks):
    out = {"todo": 0, "in_progress": 0, "done": 0}
    for t in tasks:
        s = getattr(t, "status", "") or ""
        if s in out:
            out[s] += 1
    return out


def _open_by_category(tasks, guess_fn):
    buckets = {}
    for t in tasks:
        if getattr(t, "status", "") == "done":
            continue
        cat = getattr(t, "category", None) or guess_fn(
            t.title, t.description or "", getattr(t, "due_date", None)
        )
        buckets[cat] = buckets.get(cat, 0) + 1
    return dict(sorted(buckets.items(), key=lambda x: (-x[1], x[0])))


def build_persona_dashboard(role: str, tasks: list) -> dict:
    """
    role: manager | analyst | executive
    tasks: ORM Task rows for one user (shared across personas).
    """
    now = datetime.now(timezone.utc)
    role = role.strip().lower()
    counts = _status_counts(tasks)
    done = [t for t in tasks if getattr(t, "status", "") == "done"]
    open_tasks = [t for t in tasks if getattr(t, "status", "") != "done"]
    with_due_open = [t for t in open_tasks if getattr(t, "due_date", None) is not None]

    priority = build_priority_suggestions(with_due_open, guess_category)
    productivity = build_productivity_insights(done, guess_category)
    weekly = build_weekly_retro(done, open_tasks, guess_category)
    cat_open = _open_by_category(open_tasks, guess_category)

    base = {
        "persona": role,
        "generated_at": now.isoformat(),
        "shared": {
            "task_total": len(tasks),
            "by_status": counts,
            "overdue_open_total": priority["total_overdue"],
        },
    }

    if role == "manager":
        queue = priority.get("tasks", [])[:8]
        return {
            **base,
            "lens": "operational",
            "tagline": "Day-to-day execution, blockers, and what to chase next.",
            "cards": [
                {
                    "id": "pipeline",
                    "title": "Work in motion",
                    "variant": "metric_row",
                    "metrics": [
                        {"label": "Todo", "value": counts["todo"]},
                        {"label": "In progress", "value": counts["in_progress"]},
                        {"label": "Done", "value": counts["done"]},
                    ],
                },
                {
                    "id": "risk",
                    "title": "Delivery risk",
                    "variant": "text",
                    "body": priority["suggestion"],
                    "footnote": f"{priority['total_overdue']} overdue task(s) in scope",
                },
                {
                    "id": "weekly_pulse",
                    "title": "This week pulse",
                    "variant": "bullets",
                    "items": [
                        f"Completed this week: {weekly['metrics']['completed_this_week']}",
                        f"Overdue still open: {weekly['metrics']['overdue_open_tasks']}",
                        (
                            f"Strongest bucket completed: {weekly['metrics']['top_completed_bucket']}"
                            if weekly["metrics"]["top_completed_bucket"]
                            else "No bucket stood out for completions yet."
                        ),
                    ],
                },
            ],
            "action_queue": [
                {
                    "task_id": row["id"],
                    "title": row["title"],
                    "priority": row["priority"],
                    "hours_overdue": row["hours_overdue"],
                }
                for row in queue
            ],
        }

    if role == "analyst":
        pb = productivity.get("buckets", [])
        return {
            **base,
            "lens": "quantitative",
            "tagline": "Distributions, throughput drivers, and backlog shape.",
            "cards": [
                {
                    "id": "status_mix",
                    "title": "Status distribution",
                    "variant": "key_value",
                    "items": [
                        {"key": "todo", "value": counts["todo"]},
                        {"key": "in_progress", "value": counts["in_progress"]},
                        {"key": "done", "value": counts["done"]},
                    ],
                },
                {
                    "id": "open_by_bucket",
                    "title": "Open work by planning bucket",
                    "variant": "key_value",
                    "items": [{"key": k, "value": v} for k, v in cat_open.items()],
                },
                {
                    "id": "productivity_table",
                    "title": "Completion speed by bucket (done tasks)",
                    "variant": "table",
                    "columns": ["category", "tasks_completed", "avg_hours_to_complete"],
                    "rows": pb,
                },
                {
                    "id": "productivity_story",
                    "title": "Throughput narrative",
                    "variant": "text",
                    "body": productivity.get("narrative", ""),
                },
            ],
            "datasets": {
                "status_breakdown": counts,
                "category_open_counts": cat_open,
                "productivity_buckets": pb,
            },
        }

    if role == "executive":
        m = weekly["metrics"]
        headline_parts = [
            f"{m['completed_this_week']} completed this week",
            f"{m['overdue_open_tasks']} overdue items still open",
        ]
        headline = " · ".join(headline_parts)
        return {
            **base,
            "lens": "strategic",
            "tagline": "Outcome-focused snapshot for steering conversations.",
            "headline": headline,
            "cards": [
                {
                    "id": "north_star",
                    "title": "Week at a glance",
                    "variant": "bullets",
                    "items": [
                        weekly["what_went_well"],
                        weekly["what_slipped"],
                    ],
                },
                {
                    "id": "focus",
                    "title": "Recommended focus",
                    "variant": "text",
                    "body": weekly["next_week_focus"],
                },
                {
                    "id": "signals",
                    "title": "Signals we watch",
                    "variant": "bullets",
                    "items": [
                        (
                            f"Top momentum bucket: {m['top_completed_bucket']}"
                            if m["top_completed_bucket"]
                            else "Momentum bucket not differentiated yet."
                        ),
                        (
                            f"Most slippage by bucket: {m['top_slipping_bucket']}"
                            if m["top_slipping_bucket"]
                            else "No slipped bucket stands out."
                        ),
                        f"Open backlog shape: {len(cat_open)} planning buckets with open work.",
                    ],
                },
            ],
            "weekly_metrics": m,
        }

    raise ValueError(f"unknown persona role '{role}'")

# productivity numbers from done tasks (needs completed_at filled when they hit done)
from datetime import datetime, timezone


def _bucket_for_task(task, guess_fn):
    if getattr(task, "category", None):
        return task.category
    return guess_fn(task.title, task.description or "", getattr(task, "due_date", None))


def build_productivity_insights(done_tasks, guess_fn):
    # done_tasks: ORM rows with completed_at set
    buckets = {}
    for t in done_tasks:
        if t.completed_at is None or t.created_at is None:
            continue
        cat = _bucket_for_task(t, guess_fn)
        secs = (t.completed_at - t.created_at).total_seconds()
        if secs < 0:
            continue
        hours = secs / 3600.0
        if cat not in buckets:
            buckets[cat] = {"count": 0, "total_hours": 0.0}
        buckets[cat]["count"] += 1
        buckets[cat]["total_hours"] += hours

    rows = []
    for cat, data in buckets.items():
        c = data["count"]
        avg = data["total_hours"] / c if c else 0.0
        rows.append(
            {
                "category": cat,
                "tasks_completed": c,
                "avg_hours_to_complete": round(avg, 2),
            }
        )

    rows.sort(key=lambda r: r["avg_hours_to_complete"])

    narrative = ""
    if len(rows) >= 2:
        fastest = rows[0]["category"]
        slowest = rows[-1]["category"]
        a0 = rows[0]["avg_hours_to_complete"]
        a1 = rows[-1]["avg_hours_to_complete"]
        if a0 == a1:
            narrative = (
                f"Buckets '{fastest}' and '{slowest}' look about the same speed right now "
                f"(avg {a0}h). Need more spread in real timing to say one is faster."
            )
        else:
            narrative = (
                f"You tend to complete {fastest} tasks faster than {slowest} tasks "
                f"(avg {a0}h vs {a1}h)."
            )
    elif len(rows) == 1:
        narrative = (
            f"Only enough history in the '{rows[0]['category']}' bucket so far "
            f"(avg {rows[0]['avg_hours_to_complete']}h to complete)."
        )
    else:
        narrative = "Not enough completed tasks with timestamps yet. Mark tasks done and try again."

    return {"buckets": rows, "narrative": narrative}


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _priority_label(hours_overdue: float) -> str:
    if hours_overdue >= 72:
        return "high"
    if hours_overdue >= 24:
        return "medium"
    return "low"


def build_priority_suggestions(tasks, guess_fn):
    now = datetime.now(timezone.utc)
    overdue = []
    for t in tasks:
        due_utc = _as_utc(getattr(t, "due_date", None))
        if due_utc is None:
            continue
        if due_utc >= now:
            continue
        if getattr(t, "status", "") == "done":
            continue

        overdue_hours = round((now - due_utc).total_seconds() / 3600.0, 2)
        overdue.append(
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "due_date": due_utc.isoformat(),
                "category": _bucket_for_task(t, guess_fn),
                "hours_overdue": overdue_hours,
                "priority": _priority_label(overdue_hours),
            }
        )

    overdue.sort(key=lambda row: row["due_date"])
    top = overdue[:20]

    if not top:
        suggestion = "No overdue tasks right now. You're on track."
    else:
        high = sum(1 for t in top if t["priority"] == "high")
        suggestion = (
            f"Focus on the oldest overdue tasks first. "
            f"You have {len(top)} overdue task(s) in this view, including {high} high-priority item(s)."
        )

    return {
        "generated_at": now.isoformat(),
        "total_overdue": len(overdue),
        "suggestion": suggestion,
        "tasks": top,
    }

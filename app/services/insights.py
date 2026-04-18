# productivity numbers from done tasks (needs completed_at filled when they hit done)


def _bucket_for_task(task, guess_fn):
    if getattr(task, "category", None):
        return task.category
    return guess_fn(task.title, task.description or "")


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

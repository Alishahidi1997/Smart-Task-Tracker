from datetime import datetime, timedelta, timezone


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _start_of_day_utc(dt: datetime) -> datetime:
    normalized = _as_utc(dt)
    return datetime(
        year=normalized.year,
        month=normalized.month,
        day=normalized.day,
        tzinfo=timezone.utc,
    )


def _parse_iso_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    return _as_utc(parsed)


def _task_is_open_at(task, checkpoint: datetime) -> bool:
    if getattr(task, "status", "") == "done":
        done_at = _as_utc(getattr(task, "completed_at", None))
        if done_at is not None and done_at <= checkpoint:
            return False
    return True


def build_kpi_playback(tasks, from_iso: str, to_iso: str, step: str = "day"):
    if step != "day":
        raise ValueError("only step=day is supported right now")

    from_dt = _parse_iso_utc(from_iso)
    to_dt = _parse_iso_utc(to_iso)
    if from_dt > to_dt:
        raise ValueError("'from' must be <= 'to'")

    start = _start_of_day_utc(from_dt)
    end = _start_of_day_utc(to_dt)

    snapshots = []
    cursor = start
    while cursor <= end:
        day_end = cursor + timedelta(days=1) - timedelta(microseconds=1)

        completed_today = []
        for task in tasks:
            completed_at = _as_utc(getattr(task, "completed_at", None))
            if completed_at is None:
                continue
            if cursor <= completed_at <= day_end:
                completed_today.append(task)

        cycle_hours = []
        for task in completed_today:
            created_at = _as_utc(getattr(task, "created_at", None))
            completed_at = _as_utc(getattr(task, "completed_at", None))
            if created_at is None or completed_at is None:
                continue
            secs = (completed_at - created_at).total_seconds()
            if secs >= 0:
                cycle_hours.append(secs / 3600.0)

        overdue_open_count = 0
        for task in tasks:
            due_date = _as_utc(getattr(task, "due_date", None))
            if due_date is None:
                continue
            if due_date >= day_end:
                continue
            if _task_is_open_at(task, day_end):
                overdue_open_count += 1

        avg_cycle = round(sum(cycle_hours) / len(cycle_hours), 2) if cycle_hours else None
        snapshots.append(
            {
                "at": cursor.isoformat(),
                "completion": len(completed_today),
                "overdue_count": overdue_open_count,
                "cycle_time_hours": avg_cycle,
            }
        )
        cursor += timedelta(days=1)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "step": step,
        "snapshots": snapshots,
    }

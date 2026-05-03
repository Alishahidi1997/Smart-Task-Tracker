import math
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


def _daily_snapshots_list(tasks, start: datetime, end: datetime) -> list[dict]:
    """Inclusive UTC day buckets from start through end (start/end are day starts)."""
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
    return snapshots


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n == 1:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    return mean, std


def _z_score(x: float, mean: float, std: float) -> float:
    if std < 1e-9:
        if abs(x - mean) < 1e-9:
            return 0.0
        return 3.0 if x > mean else -3.0
    return (x - mean) / std


def _confidence_from_z(z: float) -> float:
    """Map |z| to 0..1; meaningful above ~2 std."""
    a = abs(z)
    return round(min(0.99, max(0.35, 0.35 + min(0.64, (a - 1.5) * 0.18))), 2)


def _append_count_anomaly(
    anomalies: list[dict],
    *,
    metric: str,
    direction: str,
    day_iso: str,
    value: float,
    baseline_mean: float,
    z: float,
    confidence: float,
    likely_cause: str,
    min_abs_delta: float,
    abs_delta: float,
):
    if abs_delta < min_abs_delta:
        return
    impact = round(abs(z) * (1.0 + 0.12 * abs_delta), 3)
    anomalies.append(
        {
            "id": f"{metric}_{direction}_{day_iso[:10]}",
            "date": day_iso,
            "metric": metric,
            "direction": direction,
            "value": value,
            "baseline_mean": round(baseline_mean, 3),
            "z_score": round(z, 3),
            "confidence": confidence,
            "likely_cause": likely_cause,
            "impact": impact,
        }
    )


def detect_kpi_anomalies(tasks, window_days: int = 30, baseline_days: int = 7):
    """
    Flag unusual spikes/drops in daily completion, overdue backlog, and cycle time
    vs a rolling prior baseline (same metrics as KPI playback).
    """
    now = datetime.now(timezone.utc)
    end = _start_of_day_utc(now)
    start = end - timedelta(days=window_days - 1)
    snapshots = _daily_snapshots_list(tasks, start, end)

    anomalies: list[dict] = []
    z_threshold = 2.0
    count_min_delta = 1.0

    if len(snapshots) < baseline_days + 1:
        return {
            "generated_at": now.isoformat(),
            "window_days": window_days,
            "baseline_days": baseline_days,
            "snapshots_used": len(snapshots),
            "anomalies": [],
        }

    for i in range(baseline_days, len(snapshots)):
        prev = snapshots[i - baseline_days : i]
        cur = snapshots[i]
        day_iso = cur["at"]

        # completion
        b_comp = [float(s["completion"]) for s in prev]
        x_comp = float(cur["completion"])
        m_comp, s_comp = _mean_std(b_comp)
        z_comp = _z_score(x_comp, m_comp, s_comp)
        d_comp = x_comp - m_comp
        if abs(z_comp) >= z_threshold and abs(d_comp) >= count_min_delta:
            if d_comp > 0:
                _append_count_anomaly(
                    anomalies,
                    metric="completion",
                    direction="spike",
                    day_iso=day_iso,
                    value=x_comp,
                    baseline_mean=m_comp,
                    z=z_comp,
                    confidence=_confidence_from_z(z_comp),
                    likely_cause=(
                        "Daily completions jumped versus your prior-week pattern; "
                        "often a batch close-out, sprint end, or catch-up day."
                    ),
                    min_abs_delta=1.0,
                    abs_delta=abs(d_comp),
                )
            else:
                _append_count_anomaly(
                    anomalies,
                    metric="completion",
                    direction="drop",
                    day_iso=day_iso,
                    value=x_comp,
                    baseline_mean=m_comp,
                    z=z_comp,
                    confidence=_confidence_from_z(z_comp),
                    likely_cause=(
                        "Completions dipped relative to recent days; "
                        "possible context switch, blocker, or lighter workload that day."
                    ),
                    min_abs_delta=1.0,
                    abs_delta=abs(d_comp),
                )

        # overdue_count
        b_od = [float(s["overdue_count"]) for s in prev]
        x_od = float(cur["overdue_count"])
        m_od, s_od = _mean_std(b_od)
        z_od = _z_score(x_od, m_od, s_od)
        d_od = x_od - m_od
        if abs(z_od) >= z_threshold and abs(d_od) >= count_min_delta:
            if d_od > 0:
                _append_count_anomaly(
                    anomalies,
                    metric="overdue_count",
                    direction="spike",
                    day_iso=day_iso,
                    value=x_od,
                    baseline_mean=m_od,
                    z=z_od,
                    confidence=_confidence_from_z(z_od),
                    likely_cause=(
                        "Open overdue tasks increased versus your recent baseline; "
                        "due dates may have clustered or delivery slipped that day."
                    ),
                    min_abs_delta=1.0,
                    abs_delta=abs(d_od),
                )
            else:
                _append_count_anomaly(
                    anomalies,
                    metric="overdue_count",
                    direction="drop",
                    day_iso=day_iso,
                    value=x_od,
                    baseline_mean=m_od,
                    z=z_od,
                    confidence=_confidence_from_z(z_od),
                    likely_cause=(
                        "Overdue backlog shrank sharply; "
                        "often rescheduling, pay-down work, or tasks marked done."
                    ),
                    min_abs_delta=1.0,
                    abs_delta=abs(d_od),
                )

        # cycle_time_hours (only when current and baseline have signal)
        if cur["cycle_time_hours"] is None:
            continue
        x_cyc = float(cur["cycle_time_hours"])
        b_cyc = [float(s["cycle_time_hours"]) for s in prev if s.get("cycle_time_hours") is not None]
        if len(b_cyc) < 4:
            continue
        m_cyc, s_cyc = _mean_std(b_cyc)
        z_cyc = _z_score(x_cyc, m_cyc, s_cyc)
        d_cyc = x_cyc - m_cyc
        min_delta = max(0.5, 0.15 * m_cyc) if m_cyc > 0 else 0.5
        if abs(z_cyc) >= z_threshold and abs(d_cyc) >= min_delta:
            direction = "spike" if d_cyc > 0 else "drop"
            cause = (
                "Average time from create to complete was higher than your recent norm; "
                "often larger tasks, waiting, or fewer quick wins that day."
                if direction == "spike"
                else (
                    "Tasks closed faster than your recent average; "
                    "often smaller items, carry-over work, or batch completions."
                )
            )
            impact = round(abs(z_cyc) * (1.0 + 0.08 * abs(d_cyc)), 3)
            anomalies.append(
                {
                    "id": f"cycle_time_hours_{direction}_{day_iso[:10]}",
                    "date": day_iso,
                    "metric": "cycle_time_hours",
                    "direction": direction,
                    "value": x_cyc,
                    "baseline_mean": round(m_cyc, 3),
                    "z_score": round(z_cyc, 3),
                    "confidence": _confidence_from_z(z_cyc),
                    "likely_cause": cause,
                    "impact": impact,
                }
            )

    anomalies.sort(key=lambda row: row["impact"], reverse=True)

    return {
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "baseline_days": baseline_days,
        "snapshots_used": len(snapshots),
        "anomalies": anomalies,
    }


def build_kpi_playback(tasks, from_iso: str, to_iso: str, step: str = "day"):
    if step != "day":
        raise ValueError("only step=day is supported right now")

    from_dt = _parse_iso_utc(from_iso)
    to_dt = _parse_iso_utc(to_iso)
    if from_dt > to_dt:
        raise ValueError("'from' must be <= 'to'")

    start = _start_of_day_utc(from_dt)
    end = _start_of_day_utc(to_dt)
    snapshots = _daily_snapshots_list(tasks, start, end)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "step": step,
        "snapshots": snapshots,
    }

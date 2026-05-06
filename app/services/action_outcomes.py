"""Aggregations for next-action feedback (Day 24)."""

from collections import defaultdict
from datetime import datetime, timezone


def _positive_rate(accepted: int, dismissed: int, completed: int) -> float:
    total = accepted + dismissed + completed
    if total == 0:
        return 0.0
    return round((completed + 0.5 * accepted) / total, 3)


def build_next_action_outcomes_dashboard(feedback_rows, window_days: int):
    """
    feedback_rows: iterable of NextActionFeedback ORM objects with created_at, outcome, action_type, feedback_key, id
    """
    now = datetime.now(timezone.utc)
    totals = defaultdict(int)
    by_type = defaultdict(lambda: defaultdict(int))

    for row in feedback_rows:
        o = (row.outcome or "").strip().lower()
        totals[o] += 1
        totals["all"] += 1
        by_type[row.action_type][o] += 1

    breakdown = {}
    for action_type, counts in by_type.items():
        ac = counts.get("accepted", 0)
        di = counts.get("dismissed", 0)
        co = counts.get("completed", 0)
        t = ac + di + co
        breakdown[action_type] = {
            "total": t,
            "accepted": ac,
            "dismissed": di,
            "completed": co,
            "positive_rate": _positive_rate(ac, di, co),
        }

    ta = totals.get("accepted", 0)
    td = totals.get("dismissed", 0)
    tc = totals.get("completed", 0)
    t_all = ta + td + tc
    overall_positive = _positive_rate(ta, td, tc)

    if t_all == 0:
        summary = "No next-action feedback in this window yet. Mark actions as accepted, dismissed, or completed to build trends."
    else:
        summary = (
            f"In the last {window_days} day(s), you recorded {t_all} feedback event(s). "
            f"Overall positive follow-through rate is {overall_positive:.0%} "
            f"(completed + half-weighted accepted vs all outcomes)."
        )

    recent = []
    for row in sorted(feedback_rows, key=lambda r: r.created_at, reverse=True)[:20]:
        recent.append(
            {
                "id": row.id,
                "action_type": row.action_type,
                "outcome": row.outcome,
                "feedback_key": row.feedback_key,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    return {
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "totals": {
            "all": t_all,
            "accepted": ta,
            "dismissed": td,
            "completed": tc,
            "overall_positive_rate": overall_positive,
        },
        "by_action_type": dict(sorted(breakdown.items())),
        "summary": summary,
        "recent": recent,
    }

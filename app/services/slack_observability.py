"""Structured traces and lightweight metrics for the Slack orchestration path (Layer 8)."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.models import SlackOrchestrationTrace


@dataclass
class SlackTraceRecorder:
    """Collects wall-clock duration and named spans (sequential phases of one Slack request)."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spans: list[dict[str, Any]] = field(default_factory=list)
    _start: float = field(default_factory=time.perf_counter)

    def wall_duration_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)

    @contextmanager
    def span(self, name: str, **meta: Any) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            payload: dict[str, Any] = {"name": name, "duration_ms": int((time.perf_counter() - start) * 1000)}
            for k, v in meta.items():
                if v is not None:
                    payload[k] = v
            self.spans.append(payload)

    def compute_metrics(self) -> dict[str, Any]:
        wall = self.wall_duration_ms()
        spans = self.spans
        if not spans:
            return {
                "wall_duration_ms": wall,
                "span_count": 0,
                "slowest_span_ms": 0,
                "slowest_span_name": None,
                "sum_span_ms": 0,
            }
        slowest = max(spans, key=lambda x: x["duration_ms"])
        return {
            "wall_duration_ms": wall,
            "span_count": len(spans),
            "slowest_span_ms": slowest["duration_ms"],
            "slowest_span_name": slowest["name"],
            "sum_span_ms": sum(s["duration_ms"] for s in spans),
        }


def trace_response_summary(recorder: SlackTraceRecorder) -> dict[str, Any]:
    return {
        "trace_id": recorder.trace_id,
        "total_duration_ms": recorder.wall_duration_ms(),
        "span_count": len(recorder.spans),
    }


def persist_slack_trace(
    db: Session,
    recorder: SlackTraceRecorder,
    *,
    user: User | None,
    tenant_id: str,
    slack_channel_id: str | None,
    slack_message_ts: str | None,
    slack_user_id: str | None,
    outcome: str,
    audit_log_id: int | None = None,
) -> SlackOrchestrationTrace:
    metrics = recorder.compute_metrics()
    row = SlackOrchestrationTrace(
        trace_id=recorder.trace_id,
        audit_log_id=audit_log_id,
        user_id=user.id if user else None,
        tenant_id=tenant_id,
        slack_channel_id=slack_channel_id,
        slack_message_ts=slack_message_ts,
        slack_user_id=slack_user_id,
        outcome=outcome,
        total_duration_ms=metrics["wall_duration_ms"],
        spans_json=json.dumps(recorder.spans, ensure_ascii=True),
        metrics_json=json.dumps(metrics, ensure_ascii=True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

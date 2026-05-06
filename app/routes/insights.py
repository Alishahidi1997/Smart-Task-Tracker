from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import NextActionFeedback, Task, User
from app.services.action_outcomes import build_next_action_outcomes_dashboard
from app.services.analytics import detect_kpi_anomalies
from app.services.category_guess import guess_category
from app.services.insights import (
    build_insight_explanation,
    build_next_actions,
    build_priority_suggestions,
    build_productivity_insights,
)

router = APIRouter(prefix="/insights", tags=["insights"])

VALID_OUTCOMES = {"accepted", "dismissed", "completed"}


class NextActionOutcomeIn(BaseModel):
    feedback_key: str
    outcome: str


@router.get("/productivity")
def productivity_insights(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    done = (
        db.query(Task)
        .filter(Task.status == "done", Task.user_id == current_user.id)
        .order_by(Task.id.desc())
        .limit(200)
        .all()
    )
    return build_productivity_insights(done, guess_category)


@router.get("/priority")
def priority_suggestions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pending = (
        db.query(Task)
        .filter(Task.status != "done", Task.user_id == current_user.id)
        .filter(Task.due_date.is_not(None))
        .order_by(Task.due_date.asc())
        .limit(500)
        .all()
    )
    return build_priority_suggestions(pending, guess_category)


@router.get("/anomalies")
def kpi_anomalies(
    days: int = Query(default=30, ge=8, le=120),
    baseline_days: int = Query(default=7, ge=3, le=21),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if baseline_days >= days:
        raise HTTPException(
            status_code=400,
            detail="baseline_days must be smaller than days so each day has a prior window",
        )
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.created_at.asc(), Task.id.asc())
        .limit(3000)
        .all()
    )
    return detect_kpi_anomalies(tasks, window_days=days, baseline_days=baseline_days)


@router.get("/next-actions")
def next_actions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pending = (
        db.query(Task)
        .filter(Task.status != "done", Task.user_id == current_user.id)
        .filter(Task.due_date.is_not(None))
        .order_by(Task.due_date.asc())
        .limit(800)
        .all()
    )
    feedback = (
        db.query(NextActionFeedback)
        .filter(NextActionFeedback.user_id == current_user.id)
        .order_by(NextActionFeedback.id.desc())
        .limit(2000)
        .all()
    )
    return build_next_actions(pending, feedback, guess_category)


@router.post("/next-actions/outcome")
def record_next_action_outcome(
    payload: NextActionOutcomeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    outcome = payload.outcome.strip().lower()
    if outcome not in VALID_OUTCOMES:
        raise HTTPException(
            status_code=400,
            detail="outcome must be one of: accepted, dismissed, completed",
        )
    feedback_key = payload.feedback_key.strip()
    if ":" not in feedback_key:
        raise HTTPException(status_code=400, detail="feedback_key must include action_type:task_id")
    action_type = feedback_key.split(":", 1)[0].strip()
    if not action_type:
        raise HTTPException(status_code=400, detail="feedback_key missing action_type")

    row = NextActionFeedback(
        user_id=current_user.id,
        feedback_key=feedback_key,
        action_type=action_type,
        outcome=outcome,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "feedback_id": row.id, "feedback_key": feedback_key, "outcome": outcome}


@router.get("/next-actions/outcomes")
def next_action_outcomes(
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate accepted/dismissed/completed feedback used to tune next-action ranking."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(NextActionFeedback)
        .filter(
            NextActionFeedback.user_id == current_user.id,
            NextActionFeedback.created_at >= since,
        )
        .order_by(NextActionFeedback.created_at.desc())
        .limit(5000)
        .all()
    )
    return build_next_action_outcomes_dashboard(rows, window_days=days)


@router.get("/explain/{insight_id}")
def explain_insight(
    insight_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    done = (
        db.query(Task)
        .filter(Task.status == "done", Task.user_id == current_user.id)
        .order_by(Task.id.desc())
        .limit(300)
        .all()
    )
    pending = (
        db.query(Task)
        .filter(Task.status != "done", Task.user_id == current_user.id)
        .filter(Task.due_date.is_not(None))
        .order_by(Task.due_date.asc())
        .limit(500)
        .all()
    )
    explanation = build_insight_explanation(insight_id, done, pending, guess_category)
    if explanation is None:
        raise HTTPException(status_code=404, detail=f"unknown insight_id '{insight_id}'")
    return explanation

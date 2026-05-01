from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Task, User
from app.services.analytics import build_kpi_playback

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/playback")
def analytics_playback(
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    step: str = Query(default="day"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    default_to = now.date().isoformat()
    default_from = (now - timedelta(days=29)).date().isoformat()

    from_iso = from_date or default_from
    to_iso = to_date or default_to

    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .order_by(Task.created_at.asc(), Task.id.asc())
        .limit(3000)
        .all()
    )

    try:
        return build_kpi_playback(tasks, from_iso, to_iso, step)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

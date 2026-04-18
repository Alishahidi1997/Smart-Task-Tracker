from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.services.category_guess import guess_category
from app.services.insights import build_productivity_insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/productivity")
def productivity_insights(db: Session = Depends(get_db)):
    done = (
        db.query(Task)
        .filter(Task.status == "done")
        .order_by(Task.id.desc())
        .limit(200)
        .all()
    )
    return build_productivity_insights(done, guess_category)

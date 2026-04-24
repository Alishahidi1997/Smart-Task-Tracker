import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.demo_seed import reset_demo_dataset

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_EMAIL = "demo@smarttracker.local"


@router.post("/reset")
def reset_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    demo_mode = os.getenv("DEMO_MODE", "false").strip().lower() == "true"
    if not demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="demo mode is disabled",
        )
    if current_user.email != DEMO_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only demo account can reset demo data",
        )

    result = reset_demo_dataset(db, current_user)
    return {"ok": True, **result}

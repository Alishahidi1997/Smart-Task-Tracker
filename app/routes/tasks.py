from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.schemas import Status, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

# simple status workflow for updates
# todo -> in_progress -> done
# and allow reopening done back to in_progress
ALLOWED_TRANSITIONS = {
    "todo": {"todo", "in_progress"},
    "in_progress": {"in_progress", "done", "todo"},
    "done": {"done", "in_progress"},
}


def _check_status_transition(current_status: str, next_status: str):
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status workflow: {current_status} -> {next_status}",
        )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        due_date=payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    
    status_filter: Status | None = Query(default=None, alias="status"),
    due_before: datetime | None = Query(default=None),
    
    due_after: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Task)
    if status_filter is not None:
        q = q.filter(Task.status == status_filter)
    if due_before is not None:
        q = q.filter(Task.due_date.is_not(None))
        q = q.filter(Task.due_date <= due_before)

    if due_after is not None:
        q = q.filter(Task.due_date.is_not(None))
        q = q.filter(Task.due_date >= due_after)

    return q.order_by(Task.id.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    updates = payload.model_dump(exclude_unset=True)
    next_status = updates.get("status")
    if next_status is not None:
        _check_status_transition(task.status, next_status)

    for key, value in updates.items():
        setattr(task, key, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    db.delete(task)
    db.commit()
    return None

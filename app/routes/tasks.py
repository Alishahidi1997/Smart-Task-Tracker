from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task



# router = APIRouter
router = APIRouter(prefix="/tasks", tags=["tasks"])
ALLOWED_STATUS = {"todo", "in_progress",  "done"}


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str):
        text = v.strip()
        if not text:
            raise ValueError("title is required")
        return text

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str):
        text = v.strip()
        if text not in ALLOWED_STATUS:
            raise ValueError("status must be todo, in_progress, or done")
        return text


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None):
        if v is None:
            return v
        text = v.strip()
        if not text:
            raise ValueError("title cannot be blank")
        return text

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str | None):
        if v is None:
            return v
        text = v.strip()
        if text not in ALLOWED_STATUS:
            raise ValueError("status must be todo, in_progress, or done")
        return text


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title:str
    description: str | None
    status:str
    
    created_at: datetime
    due_date: datetime | None


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
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


# @router.get(f"/{task }", respone_model=taskout)
# def list_tasks(task_id: int, db)

@router.put("/{task_id}", response_model=TaskOut)

def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    updates = payload.model_dump(exclude_unset=True)
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

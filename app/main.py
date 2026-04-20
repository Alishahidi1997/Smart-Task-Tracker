from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine, migrate_sqlite
from app.models import Task
from app.routes.insights import router as insights_router
from app.routes.summary import router as summary_router
from app.routes.tasks import router as tasks_router
from app.services.category_guess import guess_category
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # import models so sqlalchemy knows about the tables
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_sqlite(engine)

    # Backfill legacy rows so smart grouping is stored on each task.
    db = SessionLocal()
    try:
        uncategorized = db.query(Task).filter(Task.category.is_(None)).all()
        for task in uncategorized:
            task.category = guess_category(task.title, task.description or "", task.due_date)
        if uncategorized:
            db.commit()
    finally:
        db.close()

    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
app.include_router(tasks_router)
app.include_router(summary_router)
app.include_router(insights_router)


@app.get("/")
def root():
    return {"status": "ok"}

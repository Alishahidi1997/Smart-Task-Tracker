from datetime import timedelta

from app.models import DailySummary, Task, User, utcnow


def reset_demo_dataset(db, user: User):
    db.query(DailySummary).filter(DailySummary.user_id == user.id).delete()
    db.query(Task).filter(Task.user_id == user.id).delete()

    now = utcnow()
    sample_tasks = [
        Task(
            title="Review API logs and fix timeout issue",
            description="Investigate slow endpoint and patch retry behavior.",
            status="done",
            created_at=now - timedelta(days=3, hours=6),
            due_date=now - timedelta(days=2),
            completed_at=now - timedelta(days=2, hours=5),
            category="today",
            user_id=user.id,
        ),
        Task(
            title="Prepare sprint planning notes",
            description="Summarize carryover and blockers for next sprint.",
            status="done",
            created_at=now - timedelta(days=6),
            due_date=now - timedelta(days=5, hours=4),
            completed_at=now - timedelta(days=5, hours=6),
            category="this_week",
            user_id=user.id,
        ),
        Task(
            title="Refactor task insights chart component",
            description="Simplify props and improve readability.",
            status="in_progress",
            created_at=now - timedelta(days=4),
            due_date=now - timedelta(days=1, hours=3),
            completed_at=None,
            category="this_week",
            user_id=user.id,
        ),
        Task(
            title="Write README deployment section",
            description="Document env vars and deploy steps.",
            status="todo",
            created_at=now - timedelta(days=1),
            due_date=now + timedelta(days=2),
            completed_at=None,
            category="backlog",
            user_id=user.id,
        ),
        Task(
            title="Morning planning and prioritization",
            description="15-minute daily review of deadlines.",
            status="done",
            created_at=now - timedelta(days=2),
            due_date=now - timedelta(days=2),
            completed_at=now - timedelta(days=2, hours=22),
            category="routine",
            user_id=user.id,
        ),
        Task(
            title="Follow up on overdue integration tests",
            description="Stabilize flaky tests in CI pipeline.",
            status="todo",
            created_at=now - timedelta(days=7),
            due_date=now - timedelta(days=1, hours=8),
            completed_at=None,
            category="today",
            user_id=user.id,
        ),
    ]

    db.add_all(sample_tasks)
    db.commit()

    return {"seeded_tasks": len(sample_tasks)}

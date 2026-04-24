# Smart Task Tracker

I wanted to build something that feels closer to a real product than a tutorial app.
So this project is a task tracker with auth, insights, and AI features that are actually useful in day-to-day planning.

You can:
- create/update/delete tasks
- track status (`todo`, `in_progress`, `done`)
- filter by due dates
- get AI daily summaries
- see overdue priority suggestions
- generate a weekly retro

It also has JWT login and user-level data isolation, so each user only sees their own data.

## Stack

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + TypeScript (Vite)
- AI: OpenAI API

## Run it locally

### Backend (terminal 1)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DEMO_MODE=true
uvicorn app.main:app --reload
```

Backend will be at:
- `http://127.0.0.1:8000`
- docs: `http://127.0.0.1:8000/docs`

If you want real AI summary output:

```bash
set OPENAI_API_KEY=your_key_here
set OPENAI_MODEL=gpt-4o-mini
```

### Frontend (terminal 2)

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`

## Demo account

Use this to try everything quickly:

- email: `demo@smarttracker.local`
- password: `demo1234`

When `DEMO_MODE=true` is enabled on backend, this account also gets a **Reset demo data** button.

## Quick note

This project is intentionally simple in setup (SQLite, single repo), but the structure is ready to scale to Postgres/deployment later.

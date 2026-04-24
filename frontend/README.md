# Smart Task Tracker (Frontend)

This is the React app for the Smart Task Tracker project.
It talks to the FastAPI backend and gives you a simple dashboard for tasks + insights.

## Quick start

From the `frontend` folder:

```bash
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`

By default it calls:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If your backend is running somewhere else, change that value in `.env`.

## What you can do in the app

- Register/login (JWT auth)
- Create, update, delete, and filter tasks
- View daily AI summary
- View productivity and priority insights
- View weekly retro

## Demo login

- Email: `demo@smarttracker.local`
- Password: `demo1234`

There is a **Reset demo data** button for this account.
It only works if backend has demo mode enabled (`DEMO_MODE=true`).

## Build

```bash
npm run build
```

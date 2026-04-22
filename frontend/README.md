# Smart Task Tracker Frontend

React + TypeScript frontend for the FastAPI Smart Task Tracker backend.

## Prerequisites

- Node.js 20+
- Backend API running at `http://127.0.0.1:8000`

## Setup

```bash
npm install
copy .env.example .env
```

Default env:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run locally

```bash
npm run dev
```

App URL: `http://localhost:5173`

## Build

```bash
npm run build
```

## Features in this UI

- Task create/list/update/delete
- Filters by status and due date window
- Daily AI summary panel
- Productivity insights panel
- Priority suggestions panel

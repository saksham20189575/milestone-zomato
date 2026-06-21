# Zomato AI Recommendations — Frontend

Next.js desktop-first UI for the Zomato AI restaurant recommendation system.

## Prerequisites

- Node.js 20.9+
- Backend API running at `http://localhost:8000`

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

## Development

Run the backend first:

```bash
# From repo root
uvicorn src.api.app:app --reload --port 8000
```

Then start the frontend:

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI backend base URL |

## Production build

```bash
npm run build
npm start
```

## Design

Visual design follows the **Epicurean Standard** system in `stitch_zomato_ai_recommendations/epicurean_standard/DESIGN.md`. The header uses the dining logo from `stitch_zomato_ai_recommendations/dining_logo/`.

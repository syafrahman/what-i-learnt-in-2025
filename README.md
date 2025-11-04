# what i learnt in 2025

A lightweight journaling wall where anyone can anonymously share what they learnt in 2025. Submissions are stored in SQLite, moderated with OpenAI, and displayed through a clean SvelteKit frontend.

## Project structure

```
backend/   FastAPI API, SQLite models, moderation logic, Dockerfile
frontend/  SvelteKit + Tailwind client ready for Vercel deployment
```

## Backend (FastAPI)

1. Copy `.env.example` to `.env` and add your OpenAI key:
   ```bash
   cd backend
   cp .env.example .env
   # edit .env and set OPENAI_API_KEY
   ```
2. (Optional) choose a custom database by setting `DATABASE_URL`. Defaults to `sqlite+aiosqlite:///submissions.db`. To target Render Postgres export `DATABASE_URL=postgres://user:password@host:port/dbname` and the app will normalize it for SQLAlchemy.
3. Install dependencies and run the API:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. The API exposes:
   - `POST /api/submit` – store & moderate a reflection (1 request / IP / 60s)
   - `GET /api/feed` – latest approved reflections
   - `GET /api/random` – single random approved reflection
   - `GET /health` – simple health check

### Docker

```
cd backend
docker build -t whatilearntin2025-api .
docker run --env-file .env -p 8000:8000 whatilearntin2025-api
```

Use Render’s native FastAPI or Docker deployment. Expose port 8000 and supply `OPENAI_API_KEY` (and optional `DATABASE_URL`). When switching from SQLite to Postgres, set `DATABASE_URL` to the new connection string and restart—tables are created automatically on startup.

## Frontend (SvelteKit)

1. Install Node dependencies (Node 18+ recommended):
   ```bash
   cd frontend
   npm install
   ```
2. Create a `.env.local` (or `.env`) with your API base URL:
   ```bash
   echo "VITE_API_BASE=https://your-backend-url.onrender.com" > .env.local
   ```
   During local development you can omit this to use the default `http://localhost:8000`.
3. Run locally or build for deployment:
   ```bash
   npm run dev -- --open
   npm run build
   npm run preview
   ```

Deploy the frontend to Vercel with the default SvelteKit settings. Remember to configure the `VITE_API_BASE` environment variable in the Vercel project settings so the client points to the Render backend.

## Notes

- Moderation uses the `gpt-4o-mini` model through the OpenAI Responses API.
- Submissions start as `pending`, then flip to `approved`/`rejected` once moderation completes.
- Rate limiting is in-memory; if you scale to multiple instances, use a shared store or edge rate limiter.

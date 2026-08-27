# AI Data Analyst

A full-stack Generative AI web application that lets users upload CSV/Excel datasets and ask
natural-language questions about them. Answers are **computed from the actual dataset** with Pandas —
the AI model plans the computation and explains the results, but never invents numbers.

## Stack

- **Frontend:** SvelteKit 2 (Svelte 5) + TypeScript, Chart.js
- **Backend:** Python, FastAPI, Pandas, SQLAlchemy
- **Database:** PostgreSQL
- **AI:** Groq API (Llama-3.3-70B via Groq)
- **Charts:** Chart.js (web UI) and matplotlib (PDF report)
- **PDF:** reportlab

## Features

1. Register / login / logout (JWT + bcrypt password hashing, server-side token revocation)
2. Upload CSV, XLSX, XLS files with strict validation (type, size, empty, corrupted files)
3. Dataset preview (rows, columns, types) — only a preview slice is sent to the browser
4. Data quality analysis: missing values, duplicates, empty columns, constant columns, outliers
5. Data cleaning with options (dedupe, fill missing, drop empty columns, trim, date conversion)
6. **Natural-language questions** — the core feature. The LLM plans the analysis; Pandas computes
   the numbers deterministically; the LLM explains the computed results.
7. Automatic statistics per column (count, mean, median, min, max, sum, std, unique)
8. Charts: bar, line, pie/doughnut, histogram, scatter — generated from computed aggregations
9. AI insights grounded in calculated facts (clearly separated from interpretation)
10. Analysis history saved per user, filterable by dataset
11. Professional PDF report with dataset summary, quality, statistics, Q&A, and embedded charts

## Architecture

The AI layer is deliberately **data-grounded** to prevent hallucinated answers:

1. The dataset is summarized (columns, types, missing counts, sample values) and sent to the LLM.
2. The LLM returns a small JSON **plan** (operation + column names) — it is told to use only the
   columns that exist in the schema.
3. Pandas executes the plan deterministically and produces the numbers (the source of truth).
4. The computed results are sent back to the LLM, which writes a concise explanation referencing
   **only** those numbers. If nothing could be computed, the model says so.

The full dataset is never sent to the model — only a bounded summary and computed results.

## Project structure

```
backend/
  app/
    api/        FastAPI routes (auth, datasets, analyses, reports) + auth dependencies
    core/       config, database, security (password hashing, JWT)
    models/     SQLAlchemy models (users, datasets, analyses, reports, revoked tokens)
    schemas/    Pydantic request/response models
    services/   dataset processing, statistics, quality, cleaning, AI plan/engine,
                Groq client, PDF generation
  storage/      uploaded files and generated reports (per-user, git-ignored)
  requirements.txt
  .env.example  environment template
frontend/
  src/
    lib/        API client, auth store, types, components (Navbar, Chart, DataTable)
    routes/     Landing, login, register, dashboard, dataset detail, analyze, history, reports
```

## Setup

### 1. PostgreSQL

Create a database and role (or reuse existing ones) and put the credentials in `backend/.env`.

```sql
CREATE ROLE ai_data_analyst WITH LOGIN PASSWORD 'your_password';
CREATE DATABASE ai_data_analyst OWNER ai_data_analyst;
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt

cp .env.example .env
# edit .env: DATABASE_URL, SECRET_KEY, GROQ_API_KEY
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs are available at http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment variables (`backend/.env`)

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Long random string used to sign JWTs |
| `DATABASE_URL` | e.g. `postgresql+psycopg2://ai_data_analyst:password@localhost:5432/ai_data_analyst` |
| `GROQ_API_KEY` | Groq API key (create one at https://console.groq.com/keys) |
| `GROQ_MODEL` | Default `llama-3.3-70b-versatile` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size (default 20) |

## API overview

```
POST /api/auth/register          register (returns token)
POST /api/auth/login             login (returns token)
POST /api/auth/logout            revoke current token
GET  /api/auth/me                current user

POST /api/datasets/upload        upload CSV/XLSX/XLS
GET  /api/datasets               list my datasets
GET  /api/datasets/{id}          dataset metadata
DELETE /api/datasets/{id}        delete dataset
GET  /api/datasets/{id}/preview  preview rows
GET  /api/datasets/{id}/statistics  per-column stats
GET  /api/datasets/{id}/quality  quality analysis
POST /api/datasets/{id}/clean    apply cleaning options

POST /api/datasets/{id}/ask      ask a natural-language question
GET  /api/analyses               analysis history (filter by ?dataset_id=)
GET  /api/analyses/{id}          one analysis

POST /api/reports                generate PDF report
GET  /api/reports                list reports
GET  /api/reports/{id}/download  download report PDF
```

## Security notes

- Passwords are hashed with bcrypt; JWT tokens are signed with a server-side secret.
- Logout adds the token to a denylist table so the token cannot be reused.
- All dataset/analysis/report queries are scoped to the authenticated user.
- Uploaded files are validated server-side (extension, size, emptiness, corruption, row limits).
- The Groq API key lives only in the backend environment; it is never exposed to the frontend.
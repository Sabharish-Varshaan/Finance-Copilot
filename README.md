# Finance Copilot

Finance Copilot is a full-stack personal finance mentor.

- Backend: FastAPI + SQLAlchemy + PostgreSQL + JWT
- Frontend: Next.js 14 + TypeScript + Tailwind

## Prerequisites

- Python 3.10+ (3.12 recommended)
- Node.js 18+ (20 recommended)
- PostgreSQL running locally on port 5432

## Repository Structure

- backend: API, database models, services, business logic
- frontend: UI, pages, client services

## Quick Setup

### 1. Create database

```bash
createdb finance_copilot
```

If `createdb` is unavailable:

```sql
CREATE DATABASE finance_copilot;
```

### 2. Configure and run backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Backend URLs:

- API base: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

Important backend env values in backend/.env:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/finance_copilot
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

### 3. Configure and run frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend URL:

- App: http://localhost:3000

Important frontend env value in frontend/.env.local:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## End-to-End Verification

1. Open http://localhost:3000/register and create an account.
2. Login at http://localhost:3000/login.
3. Complete onboarding at http://localhost:3000/onboarding.
4. Open dashboard at http://localhost:3000/dashboard.
5. Open mentor chat at http://localhost:3000/chat.

## API Endpoints

Auth:

- POST /api/v1/auth/register
- POST /api/v1/auth/login

Finance:

- PUT /api/v1/finance/profile
- GET /api/v1/finance/profile
- GET /api/v1/finance/health-score

Goals:

- POST /api/v1/goals
- GET /api/v1/goals
- PATCH /api/v1/goals/{goal_id}

Chat:

- POST /api/v1/chat
- GET /api/v1/chat/history

Nudges:

- GET /api/v1/nudges

## Troubleshooting

- Backend cannot connect to PostgreSQL:
  - Check PostgreSQL is running on localhost:5432.
  - Check database `finance_copilot` exists.
  - Verify `DATABASE_URL` in backend/.env.

- Backend permission denied for schema public:
  - Run with PostgreSQL superuser:
  - `psql finance_copilot -c "GRANT CONNECT, TEMP ON DATABASE finance_copilot TO postgres;"`
  - `psql finance_copilot -c "GRANT USAGE, CREATE ON SCHEMA public TO postgres;"`
  - `psql finance_copilot -c "ALTER SCHEMA public OWNER TO postgres;"`
  - `psql finance_copilot -c "ALTER DATABASE finance_copilot OWNER TO postgres;"`

- Frontend cannot reach backend:
  - Confirm backend is running on port 8000.
  - Confirm `NEXT_PUBLIC_API_BASE_URL` in frontend/.env.local is correct.

- Login unauthorized:
  - Verify email/password.
  - Log in again to refresh stored token.

- bcrypt/passlib issues on backend:
  - `cd backend && source venv/bin/activate && python -m pip install --upgrade --force-reinstall -r requirements.txt`

## Notes

- Default LLM provider is mock unless changed in backend env.
- Goal APIs are available; current dashboard mainly focuses on listing goals.

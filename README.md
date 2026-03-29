# Finance Copilot

Finance Copilot is a full-stack personal finance mentor that combines planning workflows with an AI assistant.

- Backend: FastAPI + SQLAlchemy + PostgreSQL + JWT
- Frontend: Next.js 14 + TypeScript + Tailwind
- Core domains: onboarding profile, money health scoring, goals, FIRE planning, contextual AI chat, nudges

## What This System Does

- Authenticates users with JWT.
- Stores and updates financial profile and investment records.
- Computes money health score in both legacy and 6-dimension formats.
- Plans goals using SIP calculations and feasibility checks.
- Generates FIRE plans with retirement target, allocation, and scenario outputs.
- Injects full user financial context into AI chat prompts.
- Produces actionable nudges from profile and score signals.

## Repository Structure

```text
Finance-Copilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                # shared API dependencies
│   │   │   ├── fire.py                # FIRE-specific helpers
│   │   │   └── v1/routes/             # versioned route handlers
│   │   ├── core/
│   │   │   ├── config.py              # environment/settings
│   │   │   └── security.py            # JWT + password security helpers
│   │   ├── database/
│   │   │   ├── session.py             # SQLAlchemy engine/session
│   │   │   ├── init_db.py             # startup DB initialization
│   │   │   └── base.py                # model imports/metadata base
│   │   ├── models/                    # SQLAlchemy entities
│   │   ├── schemas/                   # Pydantic request/response models
│   │   ├── services/                  # domain business logic
│   │   ├── modules/                   # pluggable feature modules (tax/portfolio)
│   │   └── main.py                    # FastAPI app entrypoint
│   ├── sql/                           # incremental SQL upgrades
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                           # Next.js App Router pages
│   ├── components/                    # shared + domain UI components
│   ├── services/                      # API client wrappers by domain
│   ├── hooks/                         # frontend auth and utility hooks
│   ├── lib/                           # helpers (formatting/utils)
│   ├── types/                         # frontend shared types
│   ├── middleware.ts                  # route protection
│   ├── package.json
│   └── .env.example
└── README.md
```

## Codebase Logic at a Glance

1. Frontend pages call domain API clients in `frontend/services`.
2. Requests hit FastAPI routers under `backend/app/api/v1/routes`.
3. Routers delegate to business services in `backend/app/services`.
4. Services read/write PostgreSQL via SQLAlchemy models in `backend/app/models`.
5. Responses are validated/serialized through Pydantic schemas in `backend/app/schemas`.
6. Chat and planning flows enrich outputs using profile, goals, investments, and FIRE context.
7. Startup lifecycle runs DB initialization and migrations so local setup stays consistent.

## Prerequisites

- Python 3.10 or newer
- Node.js 20.x (required by frontend)
- npm (comes with Node)
- PostgreSQL running on localhost:5432
- A PostgreSQL user with permission to create/use databases

## Dependencies

### Backend Runtime (backend/requirements.txt)

- fastapi==0.116.1
- uvicorn[standard]==0.35.0
- SQLAlchemy==2.0.43
- psycopg2-binary==2.9.10
- pydantic==2.11.7
- pydantic-settings==2.10.1
- python-jose[cryptography]==3.5.0
- passlib[bcrypt]==1.7.4
- bcrypt==4.0.1
- python-multipart==0.0.20
- email-validator==2.2.0

### Backend AI and Retrieval

- groq==1.1.2
- numpy==2.1.3
- faiss-cpu==1.11.0.post1
- sentence-transformers==3.4.1

### Frontend (frontend/package.json)

- next@14.2.26
- react@18.3.1
- react-dom@18.3.1
- axios, zustand, js-cookie
- tailwindcss, postcss, autoprefixer
- react-markdown, remark-gfm, recharts, react-hot-toast, lucide-react

## Setup and Run

### Quick Start (First-Time Setup)

Open three terminals from repository root.

### Terminal 1: PostgreSQL + Database

Create the database once:

```bash
createdb finance_copilot
```

If `createdb` is unavailable, use:

```bash
psql -U postgres -c "CREATE DATABASE finance_copilot;"
```

### Terminal 2: Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Backend will run at:

- API root: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Backend environment values (`backend/.env`) you should check:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/finance_copilot
JWT_SECRET_KEY=replace-with-secure-random-string
LLM_PROVIDER=mock
```

Optional Groq configuration:

```env
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODELS=llama-3.1-8b-instant
```

### Terminal 3: Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend will run at:

- App: http://localhost:3000

Frontend environment (`frontend/.env.local`):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Daily Run (After Initial Setup)

Use this on later days.

Backend:

```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

## Automatic Database Initialization

Backend startup automatically initializes the database through app lifespan hooks.

On each startup, it:

1. Creates all SQLAlchemy model tables if missing.
2. Applies idempotent schema upgrades with ALTER TABLE ... IF NOT EXISTS.
3. Executes SQL migration files under backend/sql in alphabetical order.
4. Retries up to 10 times (2 seconds interval) if DB is not ready.

This keeps local setup simple and avoids manual table bootstrap scripts.

## System Architecture (ASCII)

```text
┌───────────────────────────────────────────────────────────────────┐
│                           Frontend (Next.js)                     │
│  Pages: /login /register /onboarding /dashboard /chat /fire      │
│  Middleware: route protection using auth token/cookie checks      │
│  Service Layer: axios clients (auth, profile, goals, score, chat, │
│                 fire planner)                                     │
└───────────────┬───────────────────────────────────────────────────┘
                │ HTTP (Bearer JWT)
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                         │
│  Routers: /auth /finance /goals /fire-plan /chat /nudges         │
│  Startup: lifespan -> init_db()                                  │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Service Layer                            │
│  auth_service       finance_service       goal_service            │
│  fire_service       chat_service          nudge_service           │
│                                                                   │
│  Chat path also uses: finance_rules engine + prompt_builder +     │
│  optional LLM provider (mock/Groq) with user-context injection    │
└───────────────┬───────────────────────────────┬───────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐      ┌───────────────────────────────┐
│ PostgreSQL (SQLAlchemy)   │      │ External LLM Provider         │
│ users, profiles, goals,   │      │ Groq (optional, via env)      │
│ investments, chats, FIRE  │      │ fallback behavior supported   │
└───────────────────────────┘      └───────────────────────────────┘
```

## End-to-End Runtime Flow

1. User authenticates from frontend (`/login` or `/register`).
2. Backend verifies credentials and issues JWT.
3. Frontend stores token and sends authenticated requests.
4. Onboarding/profile data is persisted and used across scoring, goals, FIRE, and chat.
5. Dashboard aggregates profile health, nudges, goals, and plan signals.
6. Chat endpoint builds a context-aware prompt from user financial data before generating response.
7. FIRE planner computes target corpus, timelines, SIP, and scenario outcomes.
8. All flows share one source of truth in PostgreSQL.

## Business Logic Overview

### Auth

- Register and login flows issue JWT access tokens.
- Passwords are hashed using passlib and bcrypt.
- Protected routes use current-user dependency validation.

### Finance Profile and Score

- Profile is upserted per user and used as the system baseline.
- Investments are append-only history; latest record is used for analytics.
- Score supports:
  - Legacy 0-100 score
  - New 0-10 six-dimension score: emergency, insurance, debt, investment, retirement, savings

### Goals Planning

- Goal creation computes SIP from target, current amount, return, and timeline.
- Feasibility considers active goals and current FIRE allocation when present.
- Goal updates can trigger SIP recalculation when key fields change.

### FIRE Planning

- FIRE planner computes retirement target, years to retire, SIP, allocation, flags, and scenarios.
- Uses profile, active goals, and latest investment corpus for enriched outputs.
- Stores plan history and returns current/latest plan or selected plan by id.

### AI Chat

- Greeting/smalltalk is detected and handled separately.
- Finance rules engine runs before response generation.
- Full user context is injected into prompts:
  - profile
  - investments
  - active goals
  - FIRE context when relevant
- If LLM path fails, deterministic fallback responses are used.

### Nudges

- Nudges are generated from health-score/profile signals.
- Focus areas include emergency fund, debt ratio, savings rate, and investment behavior.

## API Endpoints

Base prefix: /api/v1

Auth:

- POST /auth/register
- POST /auth/login

Finance:

- PUT /finance/profile
- GET /finance/profile
- GET /finance/health-score?include_fire=true|false
- POST /finance/investments

Goals:

- POST /goals
- GET /goals?status=active|paused|completed|all
- PATCH /goals/{goal_id}
- DELETE /goals/{goal_id}

FIRE:

- POST /fire-plan/create
- GET /fire-plan/history
- GET /fire-plan/current
- GET /fire-plan/{plan_id}

Chat:

- POST /chat
- GET /chat/history?limit=1..200

Nudges:

- GET /nudges

## End-to-End Smoke Flow

1. Register at http://localhost:3000/register.
2. Login at http://localhost:3000/login.
3. Complete onboarding at http://localhost:3000/onboarding.
4. Open dashboard at http://localhost:3000/dashboard.
5. Add goals and optionally create a FIRE plan.
6. Open chat at http://localhost:3000/chat and ask finance questions.

## Troubleshooting

- Backend cannot connect to PostgreSQL:
  - Ensure PostgreSQL is running on localhost:5432.
  - Ensure database finance_copilot exists.
  - Verify DATABASE_URL in backend/.env.

- Backend schema permission issues:
  - Run:
  - psql finance_copilot -c "GRANT CONNECT, TEMP ON DATABASE finance_copilot TO postgres;"
  - psql finance_copilot -c "GRANT USAGE, CREATE ON SCHEMA public TO postgres;"
  - psql finance_copilot -c "ALTER SCHEMA public OWNER TO postgres;"
  - psql finance_copilot -c "ALTER DATABASE finance_copilot OWNER TO postgres;"

- Frontend cannot reach backend:
  - Confirm backend is on port 8000.
  - Confirm NEXT_PUBLIC_API_BASE_URL in frontend/.env.local.

- Frontend static build/cache issues:
  - Use Node 20.x.
  - Run: cd frontend && rm -rf .next && npm install && npm run dev

- Unauthorized after login:
  - Re-login to refresh stored token state.
  - Confirm JWT_SECRET_KEY consistency across backend restarts.

- bcrypt/passlib compatibility issues:
  - Run: cd backend && source venv/bin/activate && python -m pip install --upgrade --force-reinstall -r requirements.txt

## Notes

- Default LLM provider is mock unless changed via backend env.
- CORS is currently configured for http://localhost:3000 in backend app setup.
- Swagger is the source of truth for request and response schemas at runtime.

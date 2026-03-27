# Finance Copilot Backend

Production-ready FastAPI backend for an AI-powered personal finance mentor.

## Stack
- FastAPI
- PostgreSQL + SQLAlchemy ORM
- Pydantic
- JWT authentication


## Architecture
- `app/api/v1/routes`: API layer
- `app/services`: business logic layer
- `app/models`: SQLAlchemy models
- `app/schemas`: request/response contracts
- `app/modules`: future feature modules (tax, portfolio)

## MVP Features
- JWT auth: register/login with hashed passwords
- Financial profile create/update/read
- Money health score with weighted breakdown
- Goal planning with SIP calculation
- AI mentor chat endpoint with financial-context prompt injection
- Chat history persistence
- Nudges generation

## Run Locally (No Docker)
1. Copy environment file:
   - cp .env.example .env
2. Ensure PostgreSQL is running on localhost:5432 and create database finance_copilot.
3. Install dependencies and run server:
   - python3 -m pip install -r requirements.txt
   - python3 -m uvicorn app.main:app --reload
   - if you previously installed incompatible bcrypt, run:
     - python3 -m pip install --upgrade --force-reinstall -r requirements.txt
4. Open docs:
   - http://localhost:8000/docs

## API Endpoints
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- PUT /api/v1/finance/profile
- GET /api/v1/finance/profile
- GET /api/v1/finance/health-score
- POST /api/v1/goals
- GET /api/v1/goals
- PATCH /api/v1/goals/{goal_id}
- POST /api/v1/chat
- GET /api/v1/chat/history
- GET /api/v1/nudges

## Future Modular Extensions
- `app/modules/tax`: tax advisory and optimization
- `app/modules/portfolio`: portfolio analytics and rebalancing

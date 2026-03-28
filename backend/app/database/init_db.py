import time

from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from app.database.base import Base
from app.database.session import engine


SCHEMA_UPGRADE_STATEMENTS = (
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS retirement_age INTEGER NOT NULL DEFAULT 55;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS multiplier DOUBLE PRECISION NOT NULL DEFAULT 33.0;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS inflation_rate DOUBLE PRECISION NOT NULL DEFAULT 0.06;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS safety_buffer DOUBLE PRECISION NOT NULL DEFAULT 1.2;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS recommendation_flags TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS expected_return DOUBLE PRECISION NOT NULL DEFAULT 0.10;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS return_source VARCHAR(16) NOT NULL DEFAULT 'system';",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS insurance_coverage DOUBLE PRECISION NOT NULL DEFAULT 0;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS insurance_gap BOOLEAN NOT NULL DEFAULT FALSE;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS tax_suggestions TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS monthly_plan TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE financial_profiles ADD COLUMN IF NOT EXISTS insurance_coverage DOUBLE PRECISION NOT NULL DEFAULT 0;",
    "ALTER TABLE goals ADD COLUMN IF NOT EXISTS source VARCHAR(16) NOT NULL DEFAULT 'manual';",
    "ALTER TABLE goals ADD COLUMN IF NOT EXISTS fire_plan_id INTEGER;",
    "ALTER TABLE goals ADD COLUMN IF NOT EXISTS monthly_sip_allocated DOUBLE PRECISION NOT NULL DEFAULT 0;",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS monthly_sip_required DOUBLE PRECISION NOT NULL DEFAULT 0;",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'achievable';",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS status_description TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS underfunded BOOLEAN NOT NULL DEFAULT FALSE;",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS timeline_adjusted BOOLEAN NOT NULL DEFAULT FALSE;",
    "ALTER TABLE fire_goals ADD COLUMN IF NOT EXISTS adjusted_years INTEGER;",
)


def apply_schema_upgrades() -> None:
    # Keep startup schema updates idempotent so repeated app boots are safe.
    with engine.begin() as connection:
        for statement in SCHEMA_UPGRADE_STATEMENTS:
            connection.execute(text(statement))


def init_db(max_retries: int = 10, wait_seconds: int = 2) -> None:
    # Auto-migrate known additive schema changes on startup so deployments do not
    # require running SQL scripts manually for these columns.
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            apply_schema_upgrades()
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(wait_seconds)

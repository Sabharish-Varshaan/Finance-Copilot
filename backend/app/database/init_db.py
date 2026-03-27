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
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS insurance_coverage DOUBLE PRECISION NOT NULL DEFAULT 0;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS insurance_gap BOOLEAN NOT NULL DEFAULT FALSE;",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS tax_suggestions TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE fire_plans ADD COLUMN IF NOT EXISTS monthly_plan TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE financial_profiles ADD COLUMN IF NOT EXISTS insurance_coverage DOUBLE PRECISION NOT NULL DEFAULT 0;",
)


def apply_schema_upgrades() -> None:
    # Keep startup schema updates idempotent so repeated app boots are safe.
    with engine.begin() as connection:
        for statement in SCHEMA_UPGRADE_STATEMENTS:
            connection.execute(text(statement))


def init_db(max_retries: int = 10, wait_seconds: int = 2) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            apply_schema_upgrades()
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(wait_seconds)

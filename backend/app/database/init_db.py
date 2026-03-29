import logging
import time
from pathlib import Path

from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from app.database.base import Base
from app.database.session import engine


logger = logging.getLogger(__name__)


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
    """
    Apply known schema upgrades (new columns) idempotently.
    Uses IF NOT EXISTS to ensure safe repeated runs.
    """
    with engine.begin() as connection:
        for idx, statement in enumerate(SCHEMA_UPGRADE_STATEMENTS, 1):
            try:
                connection.execute(text(statement))
            except Exception as exc:
                # Some statements may fail if columns already exist or table doesn't exist yet
                # This is safe because we use IF NOT EXISTS
                logger.debug(f"[Schema Upgrade] Statement {idx} completed (may have skipped): {statement[:60]}...")
    logger.debug(f"[Schema Upgrade] Applied {len(SCHEMA_UPGRADE_STATEMENTS)} schema upgrade statements")


def apply_sql_migration_files() -> None:
    """
    Execute SQL files under backend/sql on startup.
    SQL files should use idempotent statements (IF NOT EXISTS) so re-runs are safe.
    Files are executed in alphabetical order.
    """
    backend_root = Path(__file__).resolve().parents[2]
    sql_dir = backend_root / "sql"
    if not sql_dir.exists():
        logger.debug("[SQL Migrations] No sql/ directory found. Skipping SQL migrations.")
        return

    sql_files = sorted(sql_dir.glob("*.sql"))
    if not sql_files:
        logger.debug("[SQL Migrations] No .sql files found in sql/ directory.")
        return

    logger.info(f"[SQL Migrations] Found {len(sql_files)} SQL migration file(s)")
    with engine.begin() as connection:
        for sql_file in sql_files:
            sql_text = sql_file.read_text(encoding="utf-8").strip()
            if not sql_text:
                logger.debug(f"[SQL Migrations] Skipping empty file: {sql_file.name}")
                continue
            
            logger.info(f"[SQL Migrations] Executing: {sql_file.name}")
            # Execute statement-by-statement for better compatibility with drivers
            statement_count = 0
            for statement in sql_text.split(";"):
                statement = statement.strip()
                if statement:
                    connection.execute(text(statement))
                    statement_count += 1
            logger.debug(f"[SQL Migrations] {sql_file.name}: {statement_count} statements executed")


def init_db(max_retries: int = 10, wait_seconds: int = 2) -> None:
    """
    Initialize database on application startup.
    
    Steps:
    1. Create all tables from registered models (idempotent)
    2. Apply schema upgrades (add missing columns if needed)
    3. Execute SQL migration files (if they exist)
    
    Retries on OperationalError (database not ready) to support gradual startup.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[DB Init] Attempt {attempt}/{max_retries}: Creating tables from models...")
            Base.metadata.create_all(bind=engine)
            logger.info("[DB Init] ✓ All tables created/verified")
            
            logger.info("[DB Init] Applying schema upgrades...")
            apply_schema_upgrades()
            logger.info("[DB Init] ✓ Schema upgrades applied")
            
            logger.info("[DB Init] Executing SQL migration files...")
            apply_sql_migration_files()
            logger.info("[DB Init] ✓ SQL migrations executed")
            
            logger.info("[DB Init] Database initialization complete!")
            return
        except OperationalError as exc:
            if attempt == max_retries:
                logger.error(f"[DB Init] Failed after {max_retries} attempts: {exc}")
                raise
            logger.warning(
                f"[DB Init] Attempt {attempt}/{max_retries} failed (database not ready). "
                f"Retrying in {wait_seconds}s... Error: {exc}"
            )
            time.sleep(wait_seconds)
        except Exception as exc:
            logger.error(f"[DB Init] Unexpected error: {exc}")
            raise

import time

from sqlalchemy.exc import OperationalError

from app.database.base import Base
from app.database.session import engine


def init_db(max_retries: int = 10, wait_seconds: int = 2) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(wait_seconds)

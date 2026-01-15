"""Database loading utilities for ARGO data."""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Iterator, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DATA_GENERATOR.config import CANONICAL_COLUMNS


@contextmanager
def _engine_context() -> Iterator[Engine]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set in environment.")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def _ensure_table(schema_df: pd.DataFrame, engine: Engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("argo_data"):
        return
    schema_df.head(0).to_sql("argo_data", engine, if_exists="replace", index=False)


def load_into_postgres(df: pd.DataFrame) -> Tuple[int, int, pd.DataFrame]:
    """Insert the provided dataframe into Postgres and return affected counts."""
    if df.empty:
        return 0, 0, pd.DataFrame(columns=CANONICAL_COLUMNS)

    with _engine_context() as engine:
        _ensure_table(df, engine)

        temp_table = "argo_data_temp"
        df.to_sql(temp_table, engine, if_exists="replace", index=False, chunksize=5000)

        column_list = ", ".join(CANONICAL_COLUMNS)
        insert_stmt = text(
            f"""
            INSERT INTO argo_data ({column_list})
            SELECT {column_list}
            FROM argo_data_temp t
            WHERE NOT EXISTS (
                SELECT 1 FROM argo_data a
                WHERE a.float_id = t.float_id
                  AND a.timestamp = t.timestamp
                  AND (a.pressure = t.pressure OR (a.pressure IS NULL AND t.pressure IS NULL))
            )
            RETURNING {column_list}
            """
        )

        with engine.begin() as connection:
            result = connection.execute(insert_stmt)
            inserted_records = result.mappings().all()
            inserted_rows = len(inserted_records)
            inserted_df = pd.DataFrame(inserted_records)
            if not inserted_df.empty:
                inserted_df = inserted_df[CANONICAL_COLUMNS]
            connection.execute(text("DROP TABLE IF EXISTS argo_data_temp"))

        total_rows = len(df)
        return total_rows, inserted_rows, inserted_df

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from backend.config import settings


def ensure_database(path: Path | None = None) -> Path:
    target = path or settings.resolved_db_path
    if not target.exists():
        if not settings.auto_generate_demo:
            raise FileNotFoundError(f"GrowthLab database does not exist: {target}")
        from scripts.generate_demo_data import generate_database

        generate_database(
            target,
            users=settings.demo_users,
            seed=settings.demo_seed,
            force=False,
        )
    return target


@contextmanager
def get_connection(*, read_only: bool = True) -> Iterator[duckdb.DuckDBPyConnection]:
    path = ensure_database()
    connection = duckdb.connect(str(path), read_only=read_only)
    try:
        yield connection
    finally:
        connection.close()


def query_df(sql: str, parameters: Mapping[str, Any] | Sequence[Any] | None = None) -> pd.DataFrame:
    with get_connection() as connection:
        return connection.execute(sql, parameters or {}).fetchdf()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def query_records(
    sql: str, parameters: Mapping[str, Any] | Sequence[Any] | None = None
) -> list[dict[str, Any]]:
    frame = query_df(sql, parameters)
    return [
        {key: _json_value(value) for key, value in row.items()} for row in frame.to_dict("records")
    ]

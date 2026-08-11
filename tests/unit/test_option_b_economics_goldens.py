from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _micro_fixture_connection() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE mart_experiment_user_value AS
        SELECT * FROM (VALUES
          ('referral_ui_simplification','c1','control',TRUE, TRUE,  4.0, 10.0),
          ('referral_ui_simplification','c2','control',FALSE,TRUE,  4.0,  2.0),
          ('referral_ui_simplification','c3','control',FALSE,FALSE, 0.0,  0.0),
          ('referral_ui_simplification','c4','control',FALSE,FALSE, 0.0,  0.0),
          ('referral_ui_simplification','t1','treatment',TRUE, TRUE, 5.0, 14.0),
          ('referral_ui_simplification','t2','treatment',TRUE, TRUE, 5.0,  8.0),
          ('referral_ui_simplification','t3','treatment',FALSE,TRUE,5.0,  2.0),
          ('referral_ui_simplification','t4','treatment',FALSE,FALSE,0.0, 0.0)
        ) AS t(
          experiment_id,assignment_user_id,group_name,retained_d7,
          retained_d1_7_window,variable_acquisition_cost,contribution30
        )
        """
    )
    return connection


def test_hand_calculated_micro_fixture_proves_itt_zero_contribution_and_per_10k() -> None:
    governed_sql = (
        PROJECT_ROOT / "sql" / "experiments" / "quality_adjusted_effects.sql"
    ).read_text(encoding="utf-8")
    with _micro_fixture_connection() as connection:
        result = connection.execute(governed_sql).fetchone()
    assert result is not None
    d7_per_10k, window_per_10k, contribution_per_10k = result
    assert d7_per_10k == pytest.approx(2_500.0)
    assert window_per_10k == pytest.approx(2_500.0)
    assert contribution_per_10k == pytest.approx(30_000.0)


def test_hand_calculated_cost_per_incremental_d7_uses_counterfactual_cost() -> None:
    with _micro_fixture_connection() as connection:
        result = connection.execute(
            """
            WITH arm AS (
              SELECT group_name,
                     COUNT(*) AS n,
                     SUM(retained_d7::INT) AS retained,
                     SUM(variable_acquisition_cost) AS cost
              FROM mart_experiment_user_value GROUP BY 1
            ), values_wide AS (
              SELECT
                MAX(n) FILTER(group_name='treatment') AS nt,
                MAX(retained) FILTER(group_name='treatment') AS rt,
                MAX(cost) FILTER(group_name='treatment') AS ct,
                MAX(n) FILTER(group_name='control') AS nc,
                MAX(retained) FILTER(group_name='control') AS rc,
                MAX(cost) FILTER(group_name='control') AS cc
              FROM arm
            )
            SELECT
              rt-nt*(rc/nc::DOUBLE) AS incremental_d7,
              ct-nt*(cc/nc::DOUBLE) AS incremental_cost,
              (ct-nt*(cc/nc::DOUBLE))/NULLIF(rt-nt*(rc/nc::DOUBLE),0)
                AS cost_per_incremental_d7
            FROM values_wide
            """
        ).fetchone()
    assert result is not None
    assert result[0] == pytest.approx(1.0)
    assert result[1] == pytest.approx(7.0)
    assert result[2] == pytest.approx(7.0)


def test_nonpositive_incremental_d7_has_no_efficiency_ratio() -> None:
    with duckdb.connect(":memory:") as connection:
        result = connection.execute(
            """
            SELECT CASE WHEN incremental_d7 > 0
                        THEN incremental_cost/incremental_d7 END
            FROM (VALUES (0.0, 7.0), (-1.0, 7.0))
                 AS fixture(incremental_d7,incremental_cost)
            """
        ).fetchall()
    assert result == [(None,), (None,)]

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from scripts.generate_demo_data import generate_database


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("growthlab-data") / "qa.duckdb"
    result = generate_database(path, users=2_000, seed=42)
    assert result["quality_failed"] == 0
    assert result["quality_checks"] >= 15
    return path


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> int | float:
    return connection.execute(query).fetchone()[0]


def test_all_built_in_data_quality_checks_pass(demo_db: Path) -> None:
    with duckdb.connect(str(demo_db), read_only=True) as connection:
        statuses = connection.execute(
            "SELECT check_name, status, observed_value FROM data_quality_runs ORDER BY check_name"
        ).fetchall()
    assert len(statuses) >= 15
    assert all(status == "pass" and observed == 0 for _, status, observed in statuses)


def test_generated_database_enforces_core_relational_and_temporal_invariants(
    demo_db: Path,
) -> None:
    with duckdb.connect(str(demo_db), read_only=True) as connection:
        assert _scalar(connection, "SELECT COUNT(*) FROM users WHERE user_id IS NULL") == 0
        assert _scalar(connection, "SELECT COUNT(*)-COUNT(DISTINCT user_id) FROM users") == 0
        assert (
            _scalar(connection, "SELECT COUNT(*)-COUNT(DISTINCT event_id) FROM growth_events") == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM growth_events e JOIN users u USING(user_id)
                WHERE CAST(e.event_at AS DATE) < u.signup_date
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM (
                  SELECT experiment_id, user_id, COUNT(*) AS n
                  FROM experiment_assignments GROUP BY 1,2 HAVING n <> 1
                )
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM experiment_outcomes o
                JOIN experiment_assignments a USING(experiment_id,user_id,group_name)
                WHERE o.observed_at < a.assigned_at
                """,
            )
            == 0
        )


def test_generated_funnels_are_monotonic_and_rates_are_bounded(demo_db: Path) -> None:
    with duckdb.connect(str(demo_db), read_only=True) as connection:
        invalid_funnels = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM referral_funnel_daily
            WHERE NOT (
              exposure_uv >= page_click_uv
              AND page_click_uv >= invite_click_uv
              AND invite_click_uv >= share_success_uv
              AND share_success_uv >= new_user_landing_uv
              AND new_user_landing_uv >= new_user_register_uv
              AND new_user_register_uv >= new_user_activate_uv
            )
            """,
        )
        assert invalid_funnels == 0
        rates = connection.execute(
            "SELECT d1,d3,d7,d1_7_window,d30 FROM retention_summary"
        ).fetchall()
        assert rates
        assert all(0 <= float(value) <= 1 for row in rates for value in row)


def test_generated_categories_and_numeric_domains_are_safe(demo_db: Path) -> None:
    with duckdb.connect(str(demo_db), read_only=True) as connection:
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM users WHERE device_type NOT IN ('phone','tablet','tv')",
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM users WHERE channel NOT IN ('organic','search_ads','social_ads','partner')",
            )
            == 0
        )
        assert (
            _scalar(connection, "SELECT COUNT(*) FROM acquired_users WHERE incentive_cost < 0") == 0
        )
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM feature_usage WHERE active_days_30 NOT BETWEEN 1 AND 30",
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM experiment_assignments WHERE hash_bucket NOT BETWEEN 0 AND 99",
            )
            == 0
        )


def test_same_seed_reproduces_analytical_outputs(tmp_path: Path) -> None:
    first = tmp_path / "first.duckdb"
    second = tmp_path / "second.duckdb"
    generate_database(first, users=2_000, seed=123)
    generate_database(second, users=2_000, seed=123)
    query = """
        SELECT
          (SELECT COUNT(*) FROM users) AS users,
          (SELECT SUM(retained_d1_7_window::INT) FROM new_user_retention) AS retained,
          (SELECT SUM(invite_click_uv) FROM referral_funnel_daily) AS invite_clicks,
          (SELECT SUM(primary_outcome::INT) FROM experiment_outcomes) AS experiment_successes,
          (SELECT ROUND(SUM(ltv30), 8) FROM acquired_users) AS ltv30
    """
    with duckdb.connect(str(first), read_only=True) as left:
        left_result = left.execute(query).fetchone()
    with duckdb.connect(str(second), read_only=True) as right:
        right_result = right.execute(query).fetchone()
    assert left_result == right_result


def test_generator_refuses_tiny_or_destructive_default_overwrite(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 2,000"):
        generate_database(tmp_path / "tiny.duckdb", users=1_999, seed=42)
    existing = tmp_path / "existing.duckdb"
    generate_database(existing, users=2_000, seed=42)
    with pytest.raises(FileExistsError):
        generate_database(existing, users=2_000, seed=42)

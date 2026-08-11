from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from scripts.generate_demo_data import generate_database

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def option_b_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("growthlab-option-b") / "qa-4242.duckdb"
    result = generate_database(path, users=2_000, seed=4_242)
    assert result["quality_failed"] == 0
    assert result["quality_checks"] >= 26
    return path


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> int | float:
    row = connection.execute(query).fetchone()
    assert row is not None
    return row[0]


def test_referral_identity_is_unified_without_orphans_or_duplicate_attribution(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM referral_edges e
                LEFT JOIN users inviter ON inviter.user_id=e.inviter_user_id
                LEFT JOIN users invitee ON invitee.user_id=e.new_user_id
                LEFT JOIN new_user_retention r ON r.user_id=e.new_user_id
                LEFT JOIN acquired_users a ON a.new_user_id=e.new_user_id
                WHERE inviter.user_id IS NULL OR invitee.user_id IS NULL
                   OR r.user_id IS NULL OR a.new_user_id IS NULL
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*)-COUNT(DISTINCT cost_event_id) FROM cost_events",
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM (
                  SELECT user_id,
                         COUNT(*) AS cost_rows,
                         COUNT(DISTINCT cost_type) AS cost_types
                  FROM cost_events GROUP BY 1
                  HAVING cost_rows <> 3 OR cost_types <> 3
                )
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                WITH cost AS (
                  SELECT user_id, SUM(amount) AS amount FROM cost_events GROUP BY 1
                ), value AS (
                  SELECT user_id,
                         SUM(gross_value) AS gross_value,
                         SUM(variable_service_cost) AS service_cost
                  FROM user_daily_value GROUP BY 1
                )
                SELECT COUNT(*)
                FROM acquired_users a
                JOIN cost c ON c.user_id=a.new_user_id
                JOIN value v ON v.user_id=a.new_user_id
                WHERE ABS(a.variable_acquisition_cost-c.amount) > 1e-9
                   OR ABS(a.ltv30-v.gross_value) > 1e-9
                   OR ABS(a.contribution30-(v.gross_value-v.service_cost-c.amount)) > 1e-9
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM cost_events c
                JOIN referral_edges e ON e.new_user_id=c.user_id
                WHERE c.referrer_user_id <> e.inviter_user_id
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM (
                  SELECT new_user_id, COUNT(*) AS n
                  FROM referral_edges GROUP BY 1 HAVING n <> 1
                )
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM (
                  SELECT new_user_id, COUNT(*) AS n
                  FROM acquired_users GROUP BY 1 HAVING n <> 1
                )
                """,
            )
            == 0
        )
        assert _scalar(connection, "SELECT COUNT(*) FROM referral_edges") == _scalar(
            connection, "SELECT COUNT(*) FROM mart_user_lifecycle"
        )
        assert _scalar(connection, "SELECT COUNT(*) FROM referral_edges") == _scalar(
            connection, "SELECT COUNT(*) FROM acquired_users"
        )


def test_referral_source_kind_separates_descriptive_and_randomized_evidence(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        domains = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT source_kind FROM referral_edges"
            ).fetchall()
        }
        assert domains == {"descriptive_campaign", "randomized_experiment"}
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM referral_edges
                WHERE (experiment_id IS NULL AND source_kind <> 'descriptive_campaign')
                   OR (experiment_id IS NOT NULL AND source_kind <> 'randomized_experiment')
                """,
            )
            == 0
        )
        descriptive_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info('mart_acquisition_quality')"
            ).fetchall()
        }
        assert not any("incremental" in column.lower() for column in descriptive_columns)


def test_lifecycle_timestamps_and_retention_flags_reconcile_to_user_day_source(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        invalid_temporal = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM referral_edges e
            JOIN users u ON u.user_id=e.new_user_id
            WHERE e.activated_date < u.signup_date
            """,
        )
        assert invalid_temporal == 0
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM user_daily_activity WHERE activity_date < signup_date",
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM experiment_exposures x
                JOIN experiment_assignments a USING(experiment_id,user_id,group_name)
                WHERE (x.was_exposed AND (x.exposed_at IS NULL OR x.exposed_at < a.assigned_at))
                   OR (NOT x.was_exposed AND x.exposed_at IS NOT NULL)
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
                LEFT JOIN experiment_exposures x USING(experiment_id,user_id,group_name)
                WHERE o.observed_at < a.assigned_at
                   OR (x.was_exposed AND o.observed_at < x.exposed_at)
                """,
            )
            == 0
        )

        mismatch_query = """
            SELECT COUNT(*)
            FROM new_user_retention r
            WHERE retained_d1 <> EXISTS(
                    SELECT 1 FROM user_daily_activity a
                    WHERE a.user_id=r.user_id AND a.relative_day=1)
               OR retained_d3 <> EXISTS(
                    SELECT 1 FROM user_daily_activity a
                    WHERE a.user_id=r.user_id AND a.relative_day=3)
               OR retained_d7 <> EXISTS(
                    SELECT 1 FROM user_daily_activity a
                    WHERE a.user_id=r.user_id AND a.relative_day=7)
               OR retained_d1_7_window <> EXISTS(
                    SELECT 1 FROM user_daily_activity a
                    WHERE a.user_id=r.user_id AND a.relative_day BETWEEN 1 AND 7)
               OR (mature_d30 AND retained_d30 <> EXISTS(
                    SELECT 1 FROM user_daily_activity a
                    WHERE a.user_id=r.user_id AND a.relative_day=30))
               OR (NOT mature_d30 AND retained_d30 IS NOT NULL)
        """
        assert _scalar(connection, mismatch_query) == 0


def test_every_acquired_user_has_reconciled_activity_value_and_all_cost_types(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM acquired_users a
                LEFT JOIN user_daily_activity d ON d.user_id=a.new_user_id
                LEFT JOIN user_daily_value v ON v.user_id=a.new_user_id
                LEFT JOIN cost_events c ON c.user_id=a.new_user_id
                WHERE d.user_id IS NULL OR v.user_id IS NULL OR c.user_id IS NULL
                """,
            )
            == 0
        )


def test_value30_is_exactly_offsets_zero_through_29_and_excludes_exact_d30(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        assert (
            _scalar(
                connection,
                "SELECT COUNT(*) FROM user_daily_value WHERE relative_day NOT BETWEEN 0 AND 29",
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM new_user_retention r
                JOIN user_daily_activity a ON a.user_id=r.user_id AND a.relative_day=30
                LEFT JOIN user_daily_value v ON v.user_id=r.user_id AND v.relative_day=30
                WHERE r.mature_d30 AND r.retained_d30 AND v.user_id IS NOT NULL
                """,
            )
            == 0
        )
        assert (
            _scalar(
                connection,
                """
                WITH value_0_29 AS (
                  SELECT user_id,
                         SUM(gross_value) AS gross_value,
                         SUM(variable_service_cost) AS service_cost
                  FROM user_daily_value
                  WHERE relative_day BETWEEN 0 AND 29
                  GROUP BY 1
                )
                SELECT COUNT(*)
                FROM acquired_users a
                JOIN value_0_29 v ON v.user_id=a.new_user_id
                WHERE ABS(a.ltv30-v.gross_value) > 1e-9
                   OR ABS(a.service_cost30-v.service_cost) > 1e-9
                """,
            )
            == 0
        )


def test_snapshot_matures_all_experiment_invitees_for_d30_and_value_followup(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        snapshot = _scalar(connection, "SELECT as_of_date FROM analysis_snapshot LIMIT 1")
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM experiment_outcomes o
                JOIN new_user_retention r ON r.user_id=o.new_user_id
                WHERE o.referred_activated
                  AND (NOT r.mature_d7 OR NOT r.mature_d30 OR r.cohort_age_days < 30)
                """,
            )
            == 0
        )
        latest_signup = _scalar(
            connection,
            """
            SELECT MAX(r.signup_date)
            FROM experiment_outcomes o
            JOIN new_user_retention r ON r.user_id=o.new_user_id
            WHERE o.referred_activated
            """,
        )
    assert snapshot >= latest_signup
    assert (snapshot - latest_signup).days >= 30


def test_itt_mart_conserves_assignments_and_nonacquirers_contribute_zero(
    option_b_db: Path,
) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        assert _scalar(connection, "SELECT COUNT(*) FROM experiment_assignments") == _scalar(
            connection, "SELECT COUNT(*) FROM mart_experiment_user_value"
        )
        assert (
            _scalar(
                connection,
                """
                SELECT COUNT(*) FROM (
                  SELECT experiment_id, assignment_user_id, COUNT(*) AS n
                  FROM mart_experiment_user_value GROUP BY 1,2 HAVING n <> 1
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
                FROM mart_experiment_user_value
                WHERE NOT referred_activated
                  AND (new_user_id IS NOT NULL
                       OR retained_d7 OR retained_d1_7_window
                       OR ABS(value30) > 1e-12
                       OR ABS(variable_acquisition_cost) > 1e-12
                       OR ABS(contribution30) > 1e-12)
                """,
            )
            == 0
        )
        for experiment_id, expected in connection.execute(
            """
            SELECT experiment_id, COUNT(*)
            FROM experiment_assignments GROUP BY 1 ORDER BY 1
            """
        ).fetchall():
            actual = _scalar(
                connection,
                f"""
                SELECT SUM(assigned_users)
                FROM mart_experiment_effects_itt
                WHERE experiment_id='{experiment_id}'
                """,
            )
            assert actual == expected


def test_quality_adjusted_sql_matches_independent_arm_level_recalculation(
    option_b_db: Path,
) -> None:
    independent_sql = """
        WITH arm AS (
          SELECT group_name,
                 COUNT(*) AS denominator,
                 SUM(retained_d7::INT) AS d7,
                 SUM(retained_d1_7_window::INT) AS d1_7,
                 SUM(contribution30) AS contribution
          FROM mart_experiment_user_value
          WHERE experiment_id='referral_ui_simplification'
          GROUP BY 1
        )
        SELECT
          10000 * (MAX(d7/denominator::DOUBLE) FILTER(group_name='treatment')
                   - MAX(d7/denominator::DOUBLE) FILTER(group_name='control')),
          10000 * (MAX(d1_7/denominator::DOUBLE) FILTER(group_name='treatment')
                   - MAX(d1_7/denominator::DOUBLE) FILTER(group_name='control')),
          10000 * (MAX(contribution/denominator::DOUBLE) FILTER(group_name='treatment')
                   - MAX(contribution/denominator::DOUBLE) FILTER(group_name='control'))
        FROM arm
    """
    governed_sql = (
        PROJECT_ROOT / "sql" / "experiments" / "quality_adjusted_effects.sql"
    ).read_text(encoding="utf-8")
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        independent = connection.execute(independent_sql).fetchone()
        governed = connection.execute(governed_sql).fetchone()
    assert independent is not None and governed is not None
    assert governed == pytest.approx(independent)


def test_acquisition_quality_segments_conserve_lifecycle_totals(option_b_db: Path) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        detail = connection.execute(
            """
            SELECT COUNT(*),
                   SUM(value30),
                   SUM(variable_acquisition_cost),
                   SUM(contribution30)
            FROM mart_user_lifecycle
            """
        ).fetchone()
        segments = connection.execute(
            """
            SELECT SUM(acquired_users),
                   SUM(total_value30),
                   SUM(total_variable_acquisition_cost),
                   SUM(total_contribution30)
            FROM mart_acquisition_quality
            """
        ).fetchone()
    assert detail is not None and segments is not None
    assert segments == pytest.approx(detail)


def test_average_ltv_cac_is_sum_value_over_sum_cost_among_acquired(option_b_db: Path) -> None:
    with duckdb.connect(str(option_b_db), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT q.acquisition_source,
                   q.acquisition_campaign,
                   q.acquisition_treatment,
                   q.average_ltv_cac,
                   SUM(l.value30)/NULLIF(SUM(l.variable_acquisition_cost),0) AS golden
            FROM mart_acquisition_quality q
            JOIN mart_user_lifecycle l
              ON l.acquisition_source=q.acquisition_source
             AND COALESCE(l.acquisition_campaign,'not_applicable')=q.acquisition_campaign
             AND COALESCE(l.acquisition_treatment,'not_applicable')=q.acquisition_treatment
            GROUP BY 1,2,3,4
            """
        ).fetchall()
    assert rows
    for *_, actual, golden in rows:
        assert actual == pytest.approx(golden)

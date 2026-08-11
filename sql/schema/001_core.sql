CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_name VARCHAR PRIMARY KEY,
    display_name_zh VARCHAR NOT NULL,
    display_name_en VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    formula VARCHAR NOT NULL,
    numerator VARCHAR,
    denominator VARCHAR,
    unit VARCHAR NOT NULL,
    grain VARCHAR NOT NULL,
    owner_role VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_runs (
    run_id VARCHAR NOT NULL,
    checked_at TIMESTAMP NOT NULL,
    check_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    observed_value DOUBLE,
    threshold VARCHAR,
    details VARCHAR
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id VARCHAR PRIMARY KEY,
    source_name VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    row_count BIGINT,
    seed INTEGER,
    status VARCHAR NOT NULL
);

-- The generator replaces these contracts with deterministic, typed snapshots.  The
-- declarations document the decision-grade grain for readers and migration tools.
CREATE TABLE IF NOT EXISTS referral_edges (
    edge_id VARCHAR PRIMARY KEY,
    inviter_user_id VARCHAR NOT NULL,
    new_user_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    activated_date DATE NOT NULL,
    source_kind VARCHAR NOT NULL,
    experiment_id VARCHAR,
    group_name VARCHAR,
    edge_status VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_exposures (
    user_id VARCHAR NOT NULL,
    experiment_id VARCHAR NOT NULL,
    group_name VARCHAR NOT NULL,
    exposure_id VARCHAR,
    was_exposed BOOLEAN NOT NULL,
    exposure_week INTEGER NOT NULL,
    exposed_at TIMESTAMP,
    PRIMARY KEY (user_id, experiment_id)
);

CREATE TABLE IF NOT EXISTS user_daily_value (
    user_id VARCHAR NOT NULL,
    value_date DATE NOT NULL,
    relative_day INTEGER NOT NULL,
    active_minutes DOUBLE NOT NULL,
    value_per_hour DOUBLE NOT NULL,
    gross_value DOUBLE NOT NULL,
    variable_service_cost DOUBLE NOT NULL,
    contribution_value DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS cost_events (
    cost_event_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    referrer_user_id VARCHAR,
    cost_date DATE NOT NULL,
    cost_type VARCHAR NOT NULL,
    amount DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_log (
    decision_id VARCHAR PRIMARY KEY,
    decision_date TIMESTAMP NOT NULL,
    growth_stage VARCHAR NOT NULL,
    business_question VARCHAR NOT NULL,
    evidence_level VARCHAR NOT NULL,
    decision VARCHAR NOT NULL,
    primary_metric VARCHAR NOT NULL,
    final_metric VARCHAR NOT NULL,
    guardrail_metric VARCHAR NOT NULL,
    fact VARCHAR NOT NULL,
    interpretation VARCHAR NOT NULL,
    hypothesis VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    limitation VARCHAR NOT NULL,
    owner_role VARCHAR NOT NULL,
    review_status VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_snapshot (
    snapshot_id VARCHAR PRIMARY KEY,
    as_of_date DATE NOT NULL,
    primary_experiment_horizon_days INTEGER NOT NULL,
    value_followup_days INTEGER NOT NULL,
    description VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dgp_policy (
    policy_id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR NOT NULL,
    treatment_path VARCHAR NOT NULL,
    downstream_quality_policy VARCHAR NOT NULL,
    cost_policy VARCHAR NOT NULL,
    known_truth VARCHAR NOT NULL,
    claim_boundary VARCHAR NOT NULL
);

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

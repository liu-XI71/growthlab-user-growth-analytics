SELECT
    experiment_id,
    group_name,
    COUNT(*) AS users,
    SUM(primary_outcome::INTEGER) AS primary_successes,
    AVG(primary_outcome::INTEGER) AS primary_rate,
    AVG(guardrail_outcome) AS guardrail_value
FROM experiment_outcomes
WHERE experiment_id = $experiment_id
GROUP BY experiment_id, group_name
ORDER BY group_name;

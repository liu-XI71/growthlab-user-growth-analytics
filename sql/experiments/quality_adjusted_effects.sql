-- Primary causal decision estimand: randomized intention-to-treat (ITT).
-- Non-acquired assignments contribute zero to quality and contribution outcomes.
WITH arm AS (
  SELECT
    experiment_id,
    group_name,
    COUNT(*) AS assigned_users,
    SUM(retained_d7::INTEGER) AS retained_d7_users,
    SUM(retained_d1_7_window::INTEGER) AS retained_d1_7_users,
    SUM(contribution30) AS contribution30
  FROM mart_experiment_user_value
  WHERE experiment_id = 'referral_ui_simplification'
  GROUP BY 1, 2
)
SELECT
  10000.0 * (
    MAX(retained_d7_users / assigned_users::DOUBLE) FILTER (group_name='treatment')
    - MAX(retained_d7_users / assigned_users::DOUBLE) FILTER (group_name='control')
  ) AS incremental_d7_retained_per_10k_assigned,
  10000.0 * (
    MAX(retained_d1_7_users / assigned_users::DOUBLE) FILTER (group_name='treatment')
    - MAX(retained_d1_7_users / assigned_users::DOUBLE) FILTER (group_name='control')
  ) AS incremental_d1_7_retained_per_10k_assigned,
  10000.0 * (
    MAX(contribution30 / assigned_users::DOUBLE) FILTER (group_name='treatment')
    - MAX(contribution30 / assigned_users::DOUBLE) FILTER (group_name='control')
  ) AS incremental_contribution30_per_10k_assigned
FROM arm;

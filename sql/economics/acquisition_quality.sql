-- Descriptive campaign quality.  This model must not be labelled causal because
-- campaign versions were launched in different time periods.
SELECT
  acquisition_source,
  acquisition_campaign,
  acquisition_treatment,
  acquired_users,
  d7_retention,
  d1_7_window_retention,
  total_value30,
  total_variable_acquisition_cost,
  average_ltv_cac,
  total_contribution30
FROM mart_acquisition_quality;

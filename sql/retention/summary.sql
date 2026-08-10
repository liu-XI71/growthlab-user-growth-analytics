SELECT
    period,
    AVG(retained_d1::INTEGER) AS d1,
    AVG(retained_d3::INTEGER) AS d3,
    AVG(retained_d7::INTEGER) AS d7,
    AVG(retained_d1_7_window::INTEGER) AS d1_7_window,
    AVG(retained_d30::INTEGER) AS d30,
    COUNT(*) AS users
FROM new_user_retention
WHERE period = $period
GROUP BY period;

SELECT
    version,
    SUM(exposure_uv) AS exposure_uv,
    SUM(page_click_uv) AS page_click_uv,
    SUM(invite_click_uv) AS invite_click_uv,
    SUM(share_success_uv) AS share_success_uv,
    SUM(new_user_landing_uv) AS new_user_landing_uv,
    SUM(new_user_register_uv) AS new_user_register_uv,
    SUM(new_user_activate_uv) AS new_user_activate_uv,
    SUM(page_click_uv)::DOUBLE / NULLIF(SUM(exposure_uv), 0) AS page_click_rate,
    SUM(invite_click_uv)::DOUBLE / NULLIF(SUM(page_click_uv), 0) AS invite_click_rate,
    SUM(share_success_uv)::DOUBLE / NULLIF(SUM(invite_click_uv), 0) AS share_success_rate,
    SUM(new_user_activate_uv)::DOUBLE / NULLIF(SUM(exposure_uv), 0) AS activation_per_exposure,
    SUM(new_user_activate_uv)::DOUBLE / NULLIF(SUM(invite_click_uv), 0) AS activation_per_invite_click
FROM referral_funnel_daily
WHERE version = $version
GROUP BY version;

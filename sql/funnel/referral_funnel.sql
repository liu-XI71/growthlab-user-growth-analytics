WITH totals AS (
    SELECT
        version,
        SUM(exposure_uv) AS campaign_exposure,
        SUM(page_click_uv) AS campaign_click,
        SUM(invite_click_uv) AS invite_click,
        SUM(share_success_uv) AS share_success,
        SUM(new_user_landing_uv) AS new_user_landing,
        SUM(new_user_register_uv) AS new_user_register,
        SUM(new_user_activate_uv) AS new_user_activate
    FROM referral_funnel_daily
    WHERE version = $version
    GROUP BY version
)
UNPIVOT totals
ON campaign_exposure, campaign_click, invite_click, share_success,
   new_user_landing, new_user_register, new_user_activate
INTO NAME step VALUE uv;

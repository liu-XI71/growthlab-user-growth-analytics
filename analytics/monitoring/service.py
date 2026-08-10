from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

ALLOWED_TREND_METRICS = {
    "dau_index",
    "external_new_index",
    "organic_new_index",
    "referral_new_index",
    "retained_user_index",
}


def analyze_growth_trend(
    frame: pd.DataFrame,
    *,
    metric: str = "dau_index",
    anomaly_threshold: float = 3.5,
) -> dict[str, Any]:
    """Return a transparent seven-day trend and robust residual anomaly score."""
    if metric not in ALLOWED_TREND_METRICS:
        raise ValueError(f"Unsupported trend metric. Choose from: {sorted(ALLOWED_TREND_METRICS)}")
    required = {"date", "target_index", metric}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing trend columns: {sorted(missing)}")
    work = frame.sort_values("date").copy()
    if len(work) < 14:
        raise ValueError("At least 14 daily observations are required")
    values = work[metric].astype(float)
    trend = values.rolling(7, center=True, min_periods=4).mean()
    trend = trend.bfill().ffill()
    residual = values - trend
    median = float(residual.median())
    mad = float(np.median(np.abs(residual - median)))
    robust_scale = 1.4826 * mad
    scores = np.zeros(len(work)) if robust_scale < 1e-12 else (residual - median) / robust_scale
    work["trend_7d"] = trend
    work["residual"] = residual
    work["anomaly_score"] = scores
    work["is_anomaly"] = np.abs(scores) >= anomaly_threshold
    work["gap_to_target"] = work["target_index"].astype(float) - values
    components = []
    for column in [
        "external_new_index",
        "organic_new_index",
        "referral_new_index",
        "retained_user_index",
    ]:
        if column not in work:
            continue
        baseline = float(work[column].head(14).mean())
        recent = float(work[column].tail(14).mean())
        components.append(
            {
                "component": column,
                "baseline_14d_average": baseline,
                "recent_14d_average": recent,
                "change": recent - baseline,
            }
        )
    items = []
    for row in work.to_dict("records"):
        items.append(
            {
                key: value.isoformat()
                if isinstance(value, (pd.Timestamp,))
                else value.item()
                if isinstance(value, np.generic)
                else value
                for key, value in row.items()
            }
        )
    latest = items[-1]
    anomalies = [item for item in items if item["is_anomaly"]]
    return {
        "metric": metric,
        "items": items,
        "latest": latest,
        "components": components,
        "anomalies": anomalies,
        "anomaly_threshold": anomaly_threshold,
        "method_note": "Seven-day centered moving trend with median-absolute-deviation residual scoring.",
        "claim_boundary": "Anomaly scores prioritize investigation; they do not identify a business cause.",
    }

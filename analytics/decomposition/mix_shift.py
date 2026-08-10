from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def mix_shift_decomposition(
    frame: pd.DataFrame,
    *,
    segment_col: str,
    period_col: str,
    outcome_col: str,
    baseline_period: str,
    current_period: str,
) -> dict[str, Any]:
    """Exact Kitagawa-style decomposition into mix, within and interaction effects."""
    required = {segment_col, period_col, outcome_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    work = frame.loc[frame[period_col].isin([baseline_period, current_period])].copy()
    if work.empty:
        raise ValueError("No rows for requested periods")
    grouped = (
        work.groupby([period_col, segment_col], observed=True)[outcome_col]
        .agg(users="size", rate="mean")
        .reset_index()
    )
    grouped["weight"] = grouped["users"] / grouped.groupby(period_col)["users"].transform("sum")
    pivot = grouped.pivot(
        index=segment_col, columns=period_col, values=["users", "rate", "weight"]
    ).fillna(0.0)
    for period in (baseline_period, current_period):
        if ("rate", period) not in pivot.columns:
            raise ValueError(f"Period has no data: {period}")
    w0 = pivot[("weight", baseline_period)].to_numpy(float)
    w1 = pivot[("weight", current_period)].to_numpy(float)
    r0 = pivot[("rate", baseline_period)].to_numpy(float)
    r1 = pivot[("rate", current_period)].to_numpy(float)
    structure = (w1 - w0) * r0
    within = w0 * (r1 - r0)
    interaction = (w1 - w0) * (r1 - r0)
    rows = []
    for idx, segment in enumerate(pivot.index):
        rows.append(
            {
                "segment": str(segment),
                "baseline_users": int(pivot.loc[segment, ("users", baseline_period)]),
                "current_users": int(pivot.loc[segment, ("users", current_period)]),
                "baseline_weight": float(w0[idx]),
                "current_weight": float(w1[idx]),
                "baseline_rate": float(r0[idx]),
                "current_rate": float(r1[idx]),
                "structure_effect": float(structure[idx]),
                "within_effect": float(within[idx]),
                "interaction_effect": float(interaction[idx]),
                "total_contribution": float(structure[idx] + within[idx] + interaction[idx]),
            }
        )
    baseline_rate = float(np.dot(w0, r0))
    current_rate = float(np.dot(w1, r1))
    return {
        "baseline_rate": baseline_rate,
        "current_rate": current_rate,
        "total_change": current_rate - baseline_rate,
        "structure_effect": float(structure.sum()),
        "within_effect": float(within.sum()),
        "interaction_effect": float(interaction.sum()),
        "reconciliation_error": float(
            (current_rate - baseline_rate) - structure.sum() - within.sum() - interaction.sum()
        ),
        "items": sorted(rows, key=lambda row: abs(row["total_contribution"]), reverse=True),
        "method_note": "Exact decomposition: mix at baseline rates + within at baseline weights + interaction.",
    }


def mix_shift_from_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the exact three-part decomposition to aggregate segment rows."""
    if not rows:
        raise ValueError("At least one segment row is required")
    frame = pd.DataFrame(rows)
    required = {"segment", "baseline_users", "current_users", "baseline_rate", "current_rate"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame["segment"].astype(str).duplicated().any():
        raise ValueError("Segments must be unique")
    count_columns = ["baseline_users", "current_users"]
    rate_columns = ["baseline_rate", "current_rate"]
    if (frame[count_columns] < 0).any().any():
        raise ValueError("User counts cannot be negative")
    if not frame[rate_columns].apply(lambda column: column.between(0, 1)).all().all():
        raise ValueError("Rates must be in [0, 1]")
    if float(frame["baseline_users"].sum()) <= 0 or float(frame["current_users"].sum()) <= 0:
        raise ValueError("Both periods require positive total users")
    frame[count_columns + rate_columns] = frame[count_columns + rate_columns].astype(float)
    w0 = frame["baseline_users"] / frame["baseline_users"].sum()
    w1 = frame["current_users"] / frame["current_users"].sum()
    r0 = frame["baseline_rate"]
    r1 = frame["current_rate"]
    structure = (w1 - w0) * r0
    within = w0 * (r1 - r0)
    interaction = (w1 - w0) * (r1 - r0)
    baseline = float((w0 * r0).sum())
    current = float((w1 * r1).sum())
    items = []
    for position, (_, row) in enumerate(frame.iterrows()):
        total = float(structure.iloc[position] + within.iloc[position] + interaction.iloc[position])
        items.append(
            {
                "segment": str(row["segment"]),
                "baseline_users": int(row["baseline_users"]),
                "current_users": int(row["current_users"]),
                "baseline_weight": float(w0.iloc[position]),
                "current_weight": float(w1.iloc[position]),
                "baseline_rate": float(r0.iloc[position]),
                "current_rate": float(r1.iloc[position]),
                "structure_effect": float(structure.iloc[position]),
                "within_effect": float(within.iloc[position]),
                "interaction_effect": float(interaction.iloc[position]),
                "total_contribution": total,
            }
        )
    total_change = current - baseline
    return {
        "baseline_rate": baseline,
        "current_rate": current,
        "total_change": total_change,
        "structure_effect": float(structure.sum()),
        "within_effect": float(within.sum()),
        "interaction_effect": float(interaction.sum()),
        "reconciliation_error": float(
            total_change - structure.sum() - within.sum() - interaction.sum()
        ),
        "items": sorted(items, key=lambda item: abs(item["total_contribution"]), reverse=True),
        "method_note": "Exact decomposition: mix at baseline rates + within at baseline weights + interaction.",
    }

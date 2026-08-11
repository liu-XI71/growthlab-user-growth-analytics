from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_decision_card(
    *,
    health: Mapping[str, bool | None],
    statistical_significant: bool,
    business_significant: bool,
    contribution_positive: bool,
    gate_reasons: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    all_inputs: dict[str, bool | None] = dict(health)
    all_inputs.update(
        {
            "statistical_significance": statistical_significant,
            "business_significance": business_significant,
            "incremental_contribution30": contribution_positive,
        }
    )
    reasons = dict(gate_reasons or {})
    gates = [
        {
            "gate": name,
            "pass": passed is True,
            "status": "pass" if passed is True else "fail" if passed is False else "unknown",
            "reason": reasons.get(
                name, "Gate passed." if passed is True else "Gate not satisfied."
            ),
        }
        for name, passed in all_inputs.items()
    ]
    all_pass = all(item["pass"] for item in gates)
    return {
        "decision": "SHIP_WITH_MONITORING" if all_pass else "DO_NOT_SHIP",
        "gates": gates,
        "all_gates_pass": all_pass,
        "failed_or_unknown_gates": [item["gate"] for item in gates if not item["pass"]],
        "monitoring": [
            "novelty durability",
            "quality-adjusted growth",
            "network interference risk",
        ],
        "principle": "A p-value never overrides assignment health, business value, or guardrails.",
    }

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import streamlit as st


def as_percent(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    number = float(value)
    if abs(number) <= 1:
        number *= 100
    return f"{number:.{digits}f}%"


def as_number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    number = float(value)
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:.{digits}f}"


def render_kpis(items: Iterable[tuple[str, Any, str | None]]) -> None:
    values = list(items)
    columns = st.columns(min(len(values), 5) or 1)
    for index, (label, value, delta) in enumerate(values):
        columns[index % len(columns)].metric(label, value, delta)


def dataframe(items: list[dict[str, Any]], *, hide_index: bool = True) -> None:
    if not items:
        st.info("当前筛选条件下暂无数据。")
        return
    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=hide_index)


def explain_result(
    facts: str,
    interpretation: str,
    hypothesis: str,
    action: str,
    limitation: str | None = None,
) -> None:
    labels = ["已确认事实", "合理解释", "待验证假设", "建议动作"]
    values = [facts, interpretation, hypothesis, action]
    if limitation is not None:
        labels.append("证据边界")
        values.append(limitation)
    tabs = st.tabs(labels)
    for tab, text in zip(tabs, values, strict=True):
        tab.write(text or "暂无")


def growth_gate(stage: str, evidence: str, claim_boundary: str) -> None:
    st.markdown(
        (
            '<div class="gl-gate">'
            f'<div><span class="gl-gate-code">{stage}</span>'
            f"<strong>证据等级：</strong>{evidence}</div>"
            f'<div class="gl-gate-boundary">{claim_boundary}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_decision_card(card: dict[str, Any]) -> None:
    decision = str(card.get("decision", "REVIEW"))
    passed = bool(card.get("all_gates_pass"))
    st.markdown(
        f'<div class="gl-decision {"gl-decision-pass" if passed else "gl-decision-hold"}">'
        f'<div class="gl-decision-label">FINAL DECISION</div><div class="gl-decision-value">{decision}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    gates = card.get("gates", [])
    if gates:
        dataframe(
            [
                {
                    "决策门": item.get("gate"),
                    "状态": "PASS" if item.get("pass") else str(item.get("status", "FAIL")).upper(),
                    "依据": item.get("reason"),
                }
                for item in gates
            ]
        )

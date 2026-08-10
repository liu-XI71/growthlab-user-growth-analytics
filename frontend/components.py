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


def explain_result(facts: str, interpretation: str, hypothesis: str, action: str) -> None:
    tabs = st.tabs(["已确认事实", "合理解释", "待验证假设", "建议动作"])
    for tab, text in zip(tabs, [facts, interpretation, hypothesis, action], strict=True):
        tab.write(text or "暂无")

from __future__ import annotations

from html import escape

import streamlit as st

COLORS = {
    "navy": "#10233D",
    "blue": "#2F6BFF",
    "cyan": "#24B6C7",
    "green": "#21A179",
    "amber": "#F5A524",
    "red": "#E5484D",
    "muted": "#64748B",
    "surface": "#F5F8FC",
}


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root { --navy: #10233d; --blue: #2f6bff; --cyan: #24b6c7; --line: #e1e8f2; }
        .stApp {
            background:
              radial-gradient(circle at 92% 3%, rgba(47,107,255,.09), transparent 25rem),
              linear-gradient(180deg, #f8fbff 0%, #f5f7fb 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0c1d35 0%, #102b4d 55%, #123758 100%);
            border-right: 1px solid rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] * { color: #f8fafc; }
        [data-testid="stSidebarNav"] a { border-radius: 10px; margin: .12rem .35rem; }
        [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); }
        .block-container { max-width: 1480px; padding-top: 1.1rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: #10233d; letter-spacing: -0.025em; }
        h2 { margin-top: 1.4rem; }
        a { color: #245eea; }
        .gl-hero {
            position: relative; overflow: hidden; margin: 0 0 1.45rem 0;
            padding: 1.35rem 1.55rem 1.25rem;
            border: 1px solid rgba(47,107,255,.16); border-radius: 20px;
            background: linear-gradient(120deg, rgba(255,255,255,.98), rgba(237,244,255,.94));
            box-shadow: 0 14px 35px rgba(16,35,61,.08);
        }
        .gl-hero::after {
            content: ""; position: absolute; width: 230px; height: 230px; right: -95px; top: -135px;
            border-radius: 50%; background: linear-gradient(135deg, rgba(47,107,255,.24), rgba(36,182,199,.10));
        }
        .gl-hero h1 { margin: .16rem 0 .28rem; font-size: clamp(1.85rem, 3vw, 2.65rem); }
        .gl-kicker { color: #2f6bff; font-weight: 750; text-transform: uppercase;
                     letter-spacing: .14em; font-size: .72rem; }
        .gl-subtitle { color: #53657c; max-width: 980px; line-height: 1.65; }
        .gl-badge {
            display: inline-block; margin-top: .75rem; padding: .22rem .58rem; border-radius: 999px;
            color: #176d64; background: #e5f8f4; font-size: .72rem; font-weight: 700;
        }
        .gl-panel { background: rgba(255,255,255,.95); border: 1px solid #e5eaf1; border-radius: 16px;
                    padding: 1rem 1.1rem; box-shadow: 0 7px 22px rgba(16,35,61,.055); }
        .gl-note { border-left: 4px solid #2f6bff; background: #eef4ff;
                   padding: .82rem 1rem; border-radius: 10px; color: #20314c;
                   white-space: pre-wrap; line-height: 1.55; }
        .gl-warning { border-left-color: #f5a524; background: #fff8e8; }
        .gl-success { border-left-color: #21a179; background: #ecfbf5; }
        .gl-danger { border-left-color: #e5484d; background: #fff0f0; }
        .gl-gate { display: grid; grid-template-columns: minmax(230px,.8fr) minmax(320px,1.8fr);
                   gap: .7rem; align-items: center; margin: -.6rem 0 1.1rem; padding: .72rem .9rem;
                   border: 1px solid #dbe7fb; border-radius: 13px; background: rgba(246,250,255,.94);
                   color: #40536b; font-size: .86rem; }
        .gl-gate-code { display: inline-flex; margin-right: .55rem; padding: .18rem .46rem;
                        border-radius: 8px; background: #10233d; color: white; font-weight: 800; }
        .gl-gate-boundary { color: #65768c; }
        .gl-decision { margin: .55rem 0 1rem; padding: 1rem 1.15rem; border-radius: 16px;
                       border: 1px solid #dce5ef; background: white; }
        .gl-decision-pass { border-left: 6px solid #21a179; background: #f0fbf7; }
        .gl-decision-hold { border-left: 6px solid #f5a524; background: #fff9ec; }
        .gl-decision-label { color: #68798e; font-size: .7rem; font-weight: 800; letter-spacing: .13em; }
        .gl-decision-value { color: #10233d; font-size: 1.45rem; font-weight: 820; letter-spacing: -.025em; }
        .gl-story-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:.6rem 0 1rem; }
        .gl-story-card { padding:.86rem .92rem; border:1px solid #e1e8f2; border-radius:14px;
                         background:rgba(255,255,255,.95); min-height:116px; }
        .gl-story-card b { display:block; color:#2f6bff; font-size:.73rem; letter-spacing:.08em;
                           margin-bottom:.3rem; }
        .gl-story-card span { color:#42546b; line-height:1.48; font-size:.88rem; }
        [data-testid="stMetric"] { background: rgba(255,255,255,.96); border: 1px solid #e1e8f2;
                                   padding: .9rem 1rem; border-radius: 15px;
                                   box-shadow: 0 8px 22px rgba(16,35,61,.055); }
        [data-testid="stMetricLabel"] { color: #5f7086; }
        [data-testid="stMetricValue"] { color: #10233d; letter-spacing: -.03em; }
        [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
            background: rgba(255,255,255,.96); border: 1px solid #e1e8f2;
            border-radius: 16px; padding: .35rem; box-shadow: 0 8px 24px rgba(16,35,61,.045);
        }
        .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid #dfe7f1; }
        .stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .55rem .85rem; }
        .stTabs [aria-selected="true"] { background: #edf3ff; color: #245eea; }
        .stButton > button, .stFormSubmitButton > button {
            border-radius: 11px; border: 1px solid rgba(47,107,255,.28); font-weight: 700;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: linear-gradient(120deg, #2f6bff, #2556d7); color: white;
            box-shadow: 0 8px 18px rgba(47,107,255,.20);
        }
        [data-testid="stExpander"] { background: rgba(255,255,255,.75); border-radius: 12px; }
        div[data-testid="stProgress"] > div > div > div { background: linear-gradient(90deg, #2f6bff, #24b6c7); }
        @media (max-width: 850px) {
            .gl-gate { grid-template-columns: 1fr; }
            .gl-story-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        (
            '<div class="gl-hero">'
            f'<div class="gl-kicker">{escape(kicker)}</div>'
            f"<h1>{escape(title)}</h1>"
            f'<div class="gl-subtitle">{escape(subtitle)}</div>'
            '<div class="gl-badge">SYNTHETIC · REPRODUCIBLE · PRIVACY-SAFE</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def note(text: str, kind: str = "note") -> None:
    extra = {"warning": "gl-warning", "success": "gl-success", "danger": "gl-danger"}.get(kind, "")
    st.markdown(f'<div class="gl-note {extra}">{escape(text)}</div>', unsafe_allow_html=True)

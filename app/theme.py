"""
CommerceIQ Analytics Studio — Visual Identity, Formatting & Plotly Theme
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

NAVY = "#17365D"
DARK_NAVY = "#0F172A"
BLUE = "#2B6CB0"
TEAL = "#0D9488"
GREEN = "#16A34A"
RED = "#DC2626"
AMBER = "#D97706"
SLATE = "#475569"

COLOR_PALETTE = [NAVY, BLUE, TEAL, AMBER, GREEN, RED, "#7C3AED", SLATE]


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #F8FAFC;
        }
        [data-testid="stSidebar"] {
            background-color: #0F172A;
        }
        [data-testid="stSidebar"] * {
            color: #E2E8F0 !important;
        }
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] *,
        [data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] *,
        [data-testid="stSidebar"] div[data-baseweb="input"] *,
        [data-testid="stSidebar"] div[data-baseweb="base-input"] *,
        [data-testid="stSidebar"] input {
            color: #0F172A !important;
        }
        .ciq-banner {
            background: linear-gradient(135deg, #0F172A 0%, #17365D 65%, #0D9488 100%);
            padding: 1.15rem 1.5rem;
            border-radius: 10px;
            color: #FFFFFF;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
        }
        .ciq-banner h1 {
            margin: 0;
            font-size: 1.6rem;
            font-weight: 700;
            color: #FFFFFF;
        }
        .ciq-banner p {
            margin: 0.25rem 0 0 0;
            font-size: 0.92rem;
            color: #CBD5E1;
        }
        .ciq-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-top: 3px solid #2B6CB0;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.75rem;
        }
        .ciq-card.good { border-top-color: #16A34A; }
        .ciq-card.warn { border-top-color: #DC2626; }
        .ciq-card.teal { border-top-color: #0D9488; }
        .ciq-card-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #64748B;
            margin-bottom: 0.25rem;
        }
        .ciq-card-value {
            font-size: 1.18rem;
            font-weight: 700;
            color: #0F172A;
            line-height: 1.25;
        }
        .ciq-card-sub {
            font-size: 0.78rem;
            color: #475569;
            margin-top: 0.2rem;
        }
        .ciq-note {
            background-color: #EFF6FF;
            border-left: 4px solid #2B6CB0;
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.88rem;
            color: #1E293B;
            margin: 0.5rem 0 1rem 0;
        }
        .ciq-disclaimer {
            background-color: #FEF3C7;
            border-left: 4px solid #D97706;
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.88rem;
            color: #78350F;
            margin: 0.5rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="ciq-banner"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", variant: str = "") -> None:
    cls = f"ciq-card {variant}".strip()
    sub_html = f'<div class="ciq-card-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="{cls}"><div class="ciq-card-label">{label}</div>'
        f'<div class="ciq-card-value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def format_brl(value: float | int | None, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "BRL 0.00"
    return f"BRL {value:,.{decimals}f}"


def style_plotly(fig: go.Figure, title: str = "", height: int = 400) -> go.Figure:
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": DARK_NAVY, "family": "Segoe UI, sans-serif"}} if title else None,
        template="plotly_white",
        height=height,
        margin={"l": 45, "r": 25, "t": 54 if title else 25, "b": 68},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#1E293B", "family": "Segoe UI, sans-serif"},
        legend={"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "center", "x": 0.5},
    )
    fig.update_xaxes(showgrid=False, linecolor="#CBD5E1")
    fig.update_yaxes(gridcolor="#F1F5F9", linecolor="#CBD5E1")
    return fig

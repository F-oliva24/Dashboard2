
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, UNIVERSE
from scoring import compute_scores
from ui import section, render_score_chart, apply_layout


CAT_COLORS = {
    "UCITS Accumulation": C["blue"],
    "ETF Accumulation":   C["green"],
    "Dividend Stocks":    C["orange"],
    "Growth Stocks":      C["purple"],
    "Macro Assets":       C["teal"],
}

# Assi radar per categoria
RADAR_AXES = {
    "UCITS Accumulation": ["Return 12M","Return 6M","Return 3M","Sharpe 1Y","Annual Vol"],
    "ETF Accumulation":   ["Return 12M","Return 6M","Return 3M","Sharpe 1Y","Annual Vol"],
    "Dividend Stocks":    ["Dividend Yield","Div Growth 5Y","Consec. Years","FCF Yield","Payout Ratio"],
    "Growth Stocks":      ["Revenue Growth","EPS Growth","ROE","Profit Margin","Momentum 6M"],
    "Macro Assets":       ["Momentum 3M","Momentum 1M","Sharpe 6M","Volatility 3M","Score"],
}


def render_radar(df: pd.DataFrame, category: str, color: str) -> None:
    """Score radar chart: mostra i top 5 asset con assi normalizzati 0-1."""
    axes = RADAR_AXES.get(category, [])
    axes_available = [a for a in axes if a in df.columns]
    if len(axes_available) < 3 or df.empty:
        return

    top5 = df.head(5)
    fig  = go.Figure()

    for i, (ticker, row) in enumerate(top5.iterrows()):
        values = []
        for ax in axes_available:
            v = pd.to_numeric(row.get(ax), errors="coerce")
            values.append(float(v) if pd.notna(v) else 0.0)

        # Normalizza 0-1 per ogni asse
        norm = []
        for j, ax in enumerate(axes_available):
            col = pd.to_numeric(df[ax], errors="coerce").dropna()
            mn, mx = col.min(), col.max()
            v = values[j]
            norm.append((v - mn) / (mx - mn) if mx > mn else 0.5)

        norm.append(norm[0])  # chiudi il poligono
        theta = axes_available + [axes_available[0]]

        # Fix: fillcolor in rgba format, hovertemplate senza f-string
        hex_color = CHART_COLORS[i % len(CHART_COLORS)]
        r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
        fill_color = f"rgba({r},{g},{b},0.2)"
        score_val = float(row.get("Score", 0)) if pd.notna(row.get("Score")) else 0.0
        trace_name = f"{ticker} ({score_val:.2f})"

        fig.add_trace(go.Scatterpolar(
            r=norm, theta=theta,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color=hex_color, width=2),
            name=trace_name,
            hovertemplate="<b>" + ticker + "</b><br>%{theta}: %{r:.2f}<extra></extra>"
        ))

    fig.update_layout(
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        font=dict(color=C["text"], family="Inter", size=11),
        polar=dict(
            bgcolor=C["card"],
            radialaxis=dict(visible=True, range=[0,1], gridcolor=C["border"],
                            linecolor=C["border"], tickfont=dict(color=C["muted"], size=9)),
            angularaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                             tickfont=dict(color=C["text"], size=10)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=C["text"])),
        height=420,
        title=dict(text=f"Radar Score — Top 5 {category}", font=dict(size=13, color=C["text"]))
    )
    st.plotly_chart(fig, use_container_width=True)


def render(is_admin: bool = True) -> None:
    st.title("🔍 Asset Screening")
    st.caption("Composite scores 0–1. Compare only within the same category. "
               "Cache: 1 hour — click '🔄 All' to force update.")

    selected = st.selectbox("Select category", list(UNIVERSE.keys()))
    color    = CAT_COLORS[selected]
    names    = UNIVERSE[selected]

    with st.spinner(f"Loading {selected}..."):
        scores = compute_scores(selected, names)

    if scores.empty:
        st.warning("No data for this category."); return

    # Bar chart + Radar side by side
    col_bar, col_radar = st.columns(2)
    with col_bar:
        render_score_chart(scores, f"Composite Score — {selected}", color)
    with col_radar:
        render_radar(scores, selected, color)

    # Tabella dati completa
    section("Full Data Table")
    fmt = scores.copy()
    for col in fmt.columns:
        if col == "Name":
            continue
        elif col == "Score":
            fmt[col] = fmt[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
        elif any(k in col for k in ["Return","Growth","Yield","Margin","ROE","Vol","Momentum"]):
            fmt[col] = fmt[col].map(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        else:
            fmt[col] = fmt[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    st.dataframe(fmt, use_container_width=True)

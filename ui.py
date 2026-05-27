"""
ui.py — Componenti UI riutilizzabili: kpi(), section(), apply_layout(),
        render_risk_charts(), render_score_chart().
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from config import C, CHART_COLORS, PLOTLY_LAYOUT
from risk import calc_risk


def apply_layout(fig, title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT, height=height,
        title=dict(text=title, font=dict(size=13, color=C["text"])))
    fig.update_xaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    fig.update_yaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    return fig


def kpi(label: str, value: str, color: str, tooltip: str = None) -> None:
    info = ""
    if tooltip:
        safe = tooltip.replace('"', "'")
        info = f' <span style="font-size:11px;color:{C["muted"]};cursor:help" title="{safe}">ℹ️</span>'
    st.markdown(
        f'<div class="kpi-box">'
        f'<div class="kpi-label">{label}{info}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def render_score_chart(df: pd.DataFrame, title: str, color: str) -> None:
    if df.empty or "Score" not in df.columns:
        st.info("No data available.")
        return
    df2    = df[["Score"]].sort_values("Score", ascending=True)
    name_c = "Name" if "Name" in df.columns else None
    labels = [f"{t} — {df.loc[t,'Name'][:25]}" if name_c else t for t in df2.index]
    fig = go.Figure(go.Bar(
        y=labels, x=df2["Score"].values, orientation="h",
        marker_color=color, opacity=0.85,
        text=[f"{v:.2f}" for v in df2["Score"].values],
        textposition="outside", textfont=dict(color=C["text"]),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>"
    ))
    fig.add_vline(x=0.5, line_color=C["muted"], line_dash="dash",
                  annotation_text="0.5", annotation_font_color=C["muted"])
    fig.update_xaxes(range=[0, 1.2])
    apply_layout(fig, title, 420)
    st.plotly_chart(fig, use_container_width=True)


def render_risk_charts(port_ret: pd.Series, total_value: float) -> dict:
    """Renderizza tutti i grafici di rischio. Restituisce r95 per uso esterno."""
    r95    = calc_risk(port_ret, total_value, 0.95, 1)
    r99_1d = calc_risk(port_ret, total_value, 0.99, 1)
    r99_20 = calc_risk(port_ret, total_value, 0.99, 20)
    r95_20 = calc_risk(port_ret, total_value, 0.95, 20)

    section("Performance")
    m1, m2, m3, m4 = st.columns(4)
    with m1: kpi("Annual Return", f"{r95['annual_return']:+.1%}",
                  C["green"] if r95["annual_return"] >= 0 else C["red"],
                  "Rendimento annualizzato basato sugli ultimi 3 anni di storia. "
                  "Calcolato come CAGR (tasso di crescita annuale composto).")
    with m2: kpi("Sharpe Ratio", f"{r95['sharpe']:.2f}", C["teal"],
                  "Rendimento ottenuto per ogni unità di rischio. "
                  "Sopra 1 = buono, sopra 2 = ottimo, sotto 0 = rischio non compensato.")
    with m3: kpi("Max Drawdown", f"{r95['max_drawdown']:.1%}", C["red"],
                  "Perdita massima dal picco al minimo nel periodo analizzato. "
                  "Es. -17% = il portafoglio ha perso il 17% dal suo massimo prima di risalire.")
    with m4: kpi("Annual Volatility", f"{r95['volatility']:.1%}", C["orange"],
                  "Oscillazione annuale del portafoglio. "
                  "Alta volatilità = maggiori fluttuazioni di prezzo giornaliere.")

    section("Value at Risk")
    v1, v2, v3 = st.columns(3)
    with v1: kpi("VaR 99% — 1 day",
                  f"€{r99_1d['var_hist_eur']:,.0f} ({r99_1d['var_hist_pct']:.2%})", C["red"],
                  f"Con il 99% di probabilità, la perdita giornaliera non supererà "
                  f"€{r99_1d['var_hist_eur']:,.0f} ({r99_1d['var_hist_pct']:.2%}). "
                  f"Solo nell'1% dei giorni storici la perdita ha superato questa soglia.")
    with v2: kpi("VaR 99% — 20 days",
                  f"€{r99_20['var_hist_eur']:,.0f} ({r99_20['var_hist_pct']:.2%})", C["red"],
                  f"Con il 99% di probabilità, la perdita mensile (~20 giorni) non supererà "
                  f"€{r99_20['var_hist_eur']:,.0f} ({r99_20['var_hist_pct']:.2%}). "
                  f"Utile per pianificare il budget mensile in scenari avversi.")
    with v3: kpi("VaR 95% — 20 days",
                  f"€{r95_20['var_hist_eur']:,.0f} ({r95_20['var_hist_pct']:.2%})", C["orange"],
                  f"Con il 95% di probabilità, la perdita mensile non supererà "
                  f"€{r95_20['var_hist_eur']:,.0f} ({r95_20['var_hist_pct']:.2%}). "
                  f"Scenario meno conservativo del VaR 99%.")

    # Grafico rendimento + drawdown
    cum_r = r95["cumulative_returns"]
    dd    = r95["drawdown_series"]
    fig_p = make_subplots(rows=2, cols=1, shared_xaxes=True,
                          row_heights=[0.65, 0.35], vertical_spacing=0.04)
    fig_p.add_trace(go.Scatter(
        x=cum_r.index, y=(cum_r - 1) * 100, name="Cumulative Return %",
        fill="tozeroy", fillcolor="rgba(0,180,255,0.12)",
        line=dict(color=C["blue"], width=2),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"
    ), row=1, col=1)
    fig_p.add_trace(go.Scatter(
        x=dd.index, y=dd.values * 100, name="Drawdown %",
        fill="tozeroy", fillcolor="rgba(255,59,59,0.2)",
        line=dict(color=C["red"], width=1.5),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"
    ), row=2, col=1)
    fig_p.update_layout(**PLOTLY_LAYOUT, height=440,
        title=dict(text="Cumulative Return & Drawdown", font=dict(size=13, color=C["text"])))
    fig_p.update_xaxes(gridcolor=C["border"])
    fig_p.update_yaxes(gridcolor=C["border"])
    st.plotly_chart(fig_p, use_container_width=True)

    # Distribuzione + correlazione
    col_d, col_c = st.columns(2)
    with col_d:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=port_ret.values * 100, nbinsx=60,
            marker_color=C["purple"], opacity=0.85
        ))
        fig_dist.add_vline(x=-r99_1d["var_hist_pct"] * 100,
            line_color=C["red"], line_width=2, line_dash="dash",
            annotation_text=f"VaR 99%: {r99_1d['var_hist_pct']:.2%}",
            annotation_font_color=C["red"])
        fig_dist.add_vline(x=-r95["var_hist_pct"] * 100,
            line_color=C["orange"], line_width=2, line_dash="dash",
            annotation_text=f"VaR 95%: {r95['var_hist_pct']:.2%}",
            annotation_font_color=C["orange"])
        apply_layout(fig_dist, "Return Distribution + VaR", 380)
        st.plotly_chart(fig_dist, use_container_width=True)

    return r95

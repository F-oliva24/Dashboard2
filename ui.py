"""
ui.py — Componenti UI: kpi(), section(), tabelle HTML custom, grafici rischio.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from config import C, CHART_COLORS, PLOTLY_LAYOUT, RANK_COLORS
from risk import calc_risk


# ------------------------------------------------------------------ #
#  BASE COMPONENTS
# ------------------------------------------------------------------ #

def apply_layout(fig, title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT, height=height,
        title=dict(text=title, font=dict(size=13, color=C["text"])))
    fig.update_xaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    fig.update_yaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    return fig


def kpi(label: str, value: str, color: str, tooltip: str = None) -> None:
    info = ""
    if tooltip:
        safe = tooltip.replace('"', "'").replace('\n', ' ')
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


# ------------------------------------------------------------------ #
#  CUSTOM HTML TABLE
# ------------------------------------------------------------------ #

def _rank_color(value, series: pd.Series, higher_is_better: bool = True) -> str:
    """Ritorna colore basato sul rank nel contesto della serie."""
    if pd.isna(value):
        return C["muted"]
    clean = series.dropna()
    if len(clean) < 3:
        return C["text"]
    p33 = clean.quantile(0.33)
    p66 = clean.quantile(0.66)
    if higher_is_better:
        if value >= p66:   return RANK_COLORS["high"]
        elif value >= p33: return RANK_COLORS["mid"]
        else:              return RANK_COLORS["low"]
    else:
        if value <= p33:   return RANK_COLORS["high"]
        elif value <= p66: return RANK_COLORS["mid"]
        else:              return RANK_COLORS["low"]


def render_table(df: pd.DataFrame,
                 rank_cols: dict = None,
                 fmt_cols: dict = None,
                 height: int = None) -> None:
    """
    Renderizza DataFrame come tabella HTML custom.

    rank_cols: {col_name: higher_is_better} — aggiunge dot colorato
    fmt_cols:  {col_name: format_fn}         — formattazione custom
    """
    if df.empty:
        st.info("No data.")
        return

    rank_cols = rank_cols or {}
    fmt_cols  = fmt_cols  or {}

    # Header
    cols_html = "".join(f"<th>{c}</th>" for c in [""] + list(df.columns))
    header    = f"<thead><tr>{cols_html}</tr></thead>"

    # Rows
    rows_html = ""
    for idx, row in df.iterrows():
        cells = f"<td><b>{idx}</b></td>"
        for col in df.columns:
            val = row[col]
            # Format
            if col in fmt_cols:
                display = fmt_cols[col](val)
            elif pd.isna(val):
                display = '<span style="color:#444">—</span>'
            else:
                display = str(val)

            # Rank dot
            if col in rank_cols and not pd.isna(val):
                try:
                    numeric_val = float(val) if isinstance(val, (int, float)) else None
                    if numeric_val is not None:
                        color = _rank_color(numeric_val, pd.to_numeric(df[col], errors="coerce"),
                                            rank_cols[col])
                        dot   = f'<span class="rank-dot" style="background:{color}"></span>'
                        display = dot + display
                except:
                    pass

            cells += f"<td>{display}</td>"
        rows_html += f"<tr>{cells}</tr>"

    style = f'style="max-height:{height}px;overflow-y:auto;display:block"' if height else ""
    html  = f'''<div {style}>
    <table class="custom-table">
      {header}
      <tbody>{rows_html}</tbody>
    </table>
    </div>'''
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  SCORE BAR CHART
# ------------------------------------------------------------------ #

def render_score_chart(df: pd.DataFrame, title: str, color: str,
                       highlight: list = None) -> None:
    """Bar chart orizzontale con score. Evidenzia ticker in highlight."""
    if df.empty or "Score" not in df.columns:
        st.info("No data."); return

    df2    = df[["Score"]].sort_values("Score", ascending=True)
    name_c = "Name" if "Name" in df.columns else None
    labels = [f"{t} — {df.loc[t,'Name'][:22]}" if name_c else t for t in df2.index]
    colors = []
    for t in df2.index:
        if highlight and t in highlight:
            colors.append(C["yellow"])
        else:
            colors.append(color)

    fig = go.Figure(go.Bar(
        y=labels, x=df2["Score"].values, orientation="h",
        marker_color=colors, opacity=0.85,
        text=[f"{v:.2f}" for v in df2["Score"].values],
        textposition="outside", textfont=dict(color=C["text"], size=11),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>"
    ))
    fig.add_vline(x=0.5, line_color=C["muted"], line_dash="dash",
                  annotation_text="Mid", annotation_font_color=C["muted"],
                  annotation_font_size=10)
    fig.update_xaxes(range=[0, 1.25])
    apply_layout(fig, title, max(320, len(df2) * 38 + 80))
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------ #
#  RISK CHARTS
# ------------------------------------------------------------------ #

def render_risk_charts(port_ret: pd.Series, total_value: float) -> dict:
    r95    = calc_risk(port_ret, total_value, 0.95, 1)
    r99_1d = calc_risk(port_ret, total_value, 0.99, 1)
    r99_20 = calc_risk(port_ret, total_value, 0.99, 20)
    r95_20 = calc_risk(port_ret, total_value, 0.95, 20)

    section("Performance")
    m1,m2,m3,m4 = st.columns(4)
    with m1: kpi("Annual Return", f"{r95['annual_return']:+.1%}",
                  C["green"] if r95["annual_return"]>=0 else C["red"],
                  "Rendimento annualizzato CAGR su 3 anni di storia.")
    with m2: kpi("Sharpe Ratio", f"{r95['sharpe']:.2f}", C["teal"],
                  "Rendimento per unità di rischio. >1 buono, >2 ottimo.")
    with m3: kpi("Max Drawdown", f"{r95['max_drawdown']:.1%}", C["red"],
                  "Perdita massima dal picco al minimo nel periodo analizzato.")
    with m4: kpi("Annual Volatility", f"{r95['volatility']:.1%}", C["orange"],
                  "Deviazione standard annualizzata dei rendimenti giornalieri.")

    section("Value at Risk")
    v1,v2,v3 = st.columns(3)
    with v1: kpi("VaR 99% — 1 day",
                  f"€{r99_1d['var_hist_eur']:,.0f} ({r99_1d['var_hist_pct']:.2%})", C["red"],
                  f"Con il 99% di probabilità la perdita giornaliera non supererà "
                  f"€{r99_1d['var_hist_eur']:,.0f}.")
    with v2: kpi("VaR 99% — 20 days",
                  f"€{r99_20['var_hist_eur']:,.0f} ({r99_20['var_hist_pct']:.2%})", C["red"],
                  f"Con il 99% di probabilità la perdita mensile non supererà "
                  f"€{r99_20['var_hist_eur']:,.0f}.")
    with v3: kpi("VaR 95% — 20 days",
                  f"€{r95_20['var_hist_eur']:,.0f} ({r95_20['var_hist_pct']:.2%})", C["orange"],
                  f"Con il 95% di probabilità la perdita mensile non supererà "
                  f"€{r95_20['var_hist_eur']:,.0f}.")

    # Charts
    cum_r = r95["cumulative_returns"]
    dd    = r95["drawdown_series"]
    fig_p = make_subplots(rows=2, cols=1, shared_xaxes=True,
                          row_heights=[0.65,0.35], vertical_spacing=0.04)
    fig_p.add_trace(go.Scatter(
        x=cum_r.index, y=(cum_r-1)*100, name="Cumulative Return %",
        fill="tozeroy", fillcolor="rgba(0,180,255,0.10)",
        line=dict(color=C["blue"], width=2),
        hovertemplate="%{x|%d %b %Y}: %{y:.2f}%<extra></extra>"
    ), row=1, col=1)
    fig_p.add_trace(go.Scatter(
        x=dd.index, y=dd.values*100, name="Drawdown %",
        fill="tozeroy", fillcolor="rgba(255,59,59,0.15)",
        line=dict(color=C["red"], width=1.5),
        hovertemplate="%{x|%d %b %Y}: %{y:.2f}%<extra></extra>"
    ), row=2, col=1)
    fig_p.update_layout(**PLOTLY_LAYOUT, height=420,
        title=dict(text="Cumulative Return & Drawdown", font=dict(size=13,color=C["text"])))
    fig_p.update_xaxes(gridcolor=C["border"])
    fig_p.update_yaxes(gridcolor=C["border"])
    st.plotly_chart(fig_p, use_container_width=True)

    col_d, col_c = st.columns(2)
    with col_d:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=port_ret.values*100, nbinsx=60,
            marker_color=C["purple"], opacity=0.8, name="Daily returns"
        ))
        fig_dist.add_vline(x=-r99_1d["var_hist_pct"]*100,
            line_color=C["red"], line_width=2, line_dash="dash",
            annotation_text=f"VaR 99%", annotation_font_color=C["red"])
        fig_dist.add_vline(x=-r95["var_hist_pct"]*100,
            line_color=C["orange"], line_width=1.5, line_dash="dash",
            annotation_text=f"VaR 95%", annotation_font_color=C["orange"])
        apply_layout(fig_dist, "Return Distribution + VaR Thresholds", 360)
        st.plotly_chart(fig_dist, use_container_width=True)

    return r95


# ------------------------------------------------------------------ #
#  NEWS RENDER
# ------------------------------------------------------------------ #

def render_news(news_items: list, max_items: int = 10) -> None:
    """Renderizza news cards con badge fonte."""
    if not news_items:
        st.info("No recent news found (last 7 days).")
        return

    shown = 0
    for item in news_items:
        if shown >= max_items:
            break
        badge_class = "source-badge trusted" if item["trusted"] else "source-badge"
        age_str     = "Today" if item["age_days"] == 0 else f"{item['age_days']}d ago"
        st.markdown(f'''
        <div class="news-card">
          <a href="{item['url']}" target="_blank" style="text-decoration:none">
            <div class="news-title">{item['title']}</div>
          </a>
          <div class="news-meta">
            <span class="{badge_class}">{item['source']}</span>
            <span>{age_str}</span>
            · <span style="color:{C['muted']}">{item['ticker']}</span>
          </div>
        </div>''', unsafe_allow_html=True)
        shown += 1


# ------------------------------------------------------------------ #
#  TOP-3 CARDS
# ------------------------------------------------------------------ #

def render_top3_cards(scores_by_cat: dict) -> None:
    """Renderizza 5 colonne con top 3 per categoria."""
    cols = st.columns(len(scores_by_cat))
    cat_colors = {
        "UCITS Accumulation": C["blue"],
        "ETF Accumulation":   C["green"],
        "Dividend Stocks":    C["orange"],
        "Growth Stocks":      C["purple"],
        "Macro Assets":       C["teal"],
    }
    medals = ["🥇", "🥈", "🥉"]

    for col, (cat, df) in zip(cols, scores_by_cat.items()):
        color = cat_colors.get(cat, C["blue"])
        with col:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:{color};'
                        f'text-transform:uppercase;letter-spacing:.08em;'
                        f'margin-bottom:10px">{cat}</div>', unsafe_allow_html=True)
            if df is None or df.empty:
                st.markdown('<div style="color:#444;font-size:12px">No data</div>',
                            unsafe_allow_html=True)
                continue
            top3 = df.head(3)
            for i, (ticker, row) in enumerate(top3.iterrows()):
                name  = str(row.get("Name",""))[:22] if "Name" in row else ticker
                score = float(row.get("Score", 0)) if pd.notna(row.get("Score")) else 0
                st.markdown(f'''
                <div class="top3-card">
                  <div class="top3-rank" style="color:{color}">{medals[i]}</div>
                  <div class="top3-name">{ticker}</div>
                  <div class="top3-score">{name}</div>
                  <div style="margin-top:6px">
                    <span style="font-size:11px;color:{color};font-weight:700">
                      Score: {score:.2f}
                    </span>
                  </div>
                </div>''', unsafe_allow_html=True)

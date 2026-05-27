"""
pages/page_screening.py — Asset Screening.
Layout espanso, indicatori colorati per rank, radar chart.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, UNIVERSE, RANK_COLORS
from scoring import compute_scores
from ui import section, apply_layout, render_table

CAT_COLORS = {
    "UCITS Accumulation": C["blue"],
    "ETF Accumulation":   C["green"],
    "Dividend Stocks":    C["orange"],
    "Growth Stocks":      C["purple"],
    "Macro Assets":       C["teal"],
}

RADAR_AXES = {
    "UCITS Accumulation": ["Return 12M","Return 6M","Return 3M","Sharpe 1Y","Annual Vol"],
    "ETF Accumulation":   ["Return 12M","Return 6M","Return 3M","Sharpe 1Y","Annual Vol"],
    "Dividend Stocks":    ["Dividend Yield","Div Growth 5Y","Consec. Years","FCF Yield","Payout Ratio"],
    "Growth Stocks":      ["Revenue Growth","EPS Growth","ROE","Profit Margin","Momentum 6M"],
    "Macro Assets":       ["Momentum 3M","Momentum 1M","Sharpe 6M","Volatility 3M","Score"],
}

# Colonne da mostrare per categoria
DISPLAY_COLS = {
    "UCITS Accumulation": {
        "Name":        ("Name",        False, None),
        "Return 1M":   ("Return 1M",   True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 3M":   ("Return 3M",   True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 6M":   ("Return 6M",   True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 12M":  ("Return 12M",  True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Sharpe 1Y":   ("Sharpe 1Y",   True,  lambda x: f"{x:.2f}"  if pd.notna(x) else "—"),
        "Annual Vol":  ("Annual Vol",  False, lambda x: f"{x:.1%}"  if pd.notna(x) else "—"),
        "Score":       ("Score",       True,  lambda x: f"{x:.3f}"  if pd.notna(x) else "—"),
    },
    "ETF Accumulation": {
        "Name":       ("Name",       False, None),
        "Return 1M":  ("Return 1M",  True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 3M":  ("Return 3M",  True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 6M":  ("Return 6M",  True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Return 12M": ("Return 12M", True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Sharpe 1Y":  ("Sharpe 1Y",  True,  lambda x: f"{x:.2f}"  if pd.notna(x) else "—"),
        "Annual Vol": ("Annual Vol", False, lambda x: f"{x:.1%}"  if pd.notna(x) else "—"),
        "Score":      ("Score",      True,  lambda x: f"{x:.3f}"  if pd.notna(x) else "—"),
    },
    "Dividend Stocks": {
        "Name":           ("Name",           False, None),
        "Dividend Yield": ("Dividend Yield", True,  lambda x: f"{x:.2%}" if pd.notna(x) else "—"),
        "Div Growth 5Y":  ("Div Growth 5Y",  True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Consec. Years":  ("Consec. Years",  True,  lambda x: f"{int(x)}y" if pd.notna(x) else "—"),
        "Payout Ratio":   ("Payout Ratio",   False, lambda x: f"{x:.0%}" if pd.notna(x) else "—"),
        "FCF Yield":      ("FCF Yield",      True,  lambda x: f"{x:.2%}" if pd.notna(x) else "—"),
        "Debt/Equity":    ("Debt/Equity",    False, lambda x: f"{x:.1f}"  if pd.notna(x) else "—"),
        "Score":          ("Score",          True,  lambda x: f"{x:.3f}"  if pd.notna(x) else "—"),
    },
    "Growth Stocks": {
        "Name":           ("Name",           False, None),
        "Revenue Growth": ("Revenue Growth", True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "EPS Growth":     ("EPS Growth",     True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "ROE":            ("ROE",            True,  lambda x: f"{x:.1%}"  if pd.notna(x) else "—"),
        "Profit Margin":  ("Profit Margin",  True,  lambda x: f"{x:.1%}"  if pd.notna(x) else "—"),
        "Forward P/E":    ("Forward P/E",    False, lambda x: f"{x:.1f}"  if pd.notna(x) else "—"),
        "Analyst Upside": ("Analyst Upside", True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Score":          ("Score",          True,  lambda x: f"{x:.3f}"  if pd.notna(x) else "—"),
    },
    "Macro Assets": {
        "Name":          ("Name",          False, None),
        "Momentum 1M":   ("Momentum 1M",   True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Momentum 3M":   ("Momentum 3M",   True,  lambda x: f"{x:+.1%}" if pd.notna(x) else "—"),
        "Sharpe 6M":     ("Sharpe 6M",     True,  lambda x: f"{x:.2f}"  if pd.notna(x) else "—"),
        "Volatility 3M": ("Volatility 3M", False, lambda x: f"{x:.1%}"  if pd.notna(x) else "—"),
        "Score":         ("Score",         True,  lambda x: f"{x:.3f}"  if pd.notna(x) else "—"),
    },
}


def render_radar(df: pd.DataFrame, category: str, color: str) -> None:
    axes = [a for a in RADAR_AXES.get(category,[]) if a in df.columns]
    if len(axes) < 3 or df.empty: return

    top5 = df.head(5)
    fig  = go.Figure()
    for i, (ticker, row) in enumerate(top5.iterrows()):
        norm = []
        for ax in axes:
            col  = pd.to_numeric(df[ax], errors="coerce").dropna()
            v    = pd.to_numeric(row.get(ax), errors="coerce")
            mn,mx = col.min(), col.max()
            norm.append((float(v)-mn)/(mx-mn) if (pd.notna(v) and mx>mn) else 0.5)
        norm.append(norm[0])
        theta = axes + [axes[0]]
        hx    = CHART_COLORS[i%len(CHART_COLORS)]
        r,g,b = int(hx[1:3],16), int(hx[3:5],16), int(hx[5:7],16)
        score = float(row.get("Score",0)) if pd.notna(row.get("Score")) else 0
        fig.add_trace(go.Scatterpolar(
            r=norm, theta=theta, fill="toself",
            fillcolor=f"rgba({r},{g},{b},0.15)",
            line=dict(color=hx, width=2),
            name=f"{ticker} ({score:.2f})",
            hovertemplate="<b>" + ticker + "</b><br>%{theta}: %{r:.2f}<extra></extra>"
        ))
    fig.update_layout(
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        font=dict(color=C["text"], family="Inter", size=11),
        polar=dict(
            bgcolor="#0a0a0a",
            radialaxis=dict(visible=True, range=[0,1],
                            gridcolor=C["border"], linecolor=C["border"],
                            tickfont=dict(color=C["muted"],size=9)),
            angularaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                             tickfont=dict(color=C["text"],size=10)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=C["text"],size=11)),
        height=400,
        title=dict(text=f"Radar — Top 5 {category}", font=dict(size=13,color=C["text"]))
    )
    st.plotly_chart(fig, use_container_width=True)


def render(is_admin: bool = True) -> None:
    st.title("🔍 Asset Screening")
    st.caption(
        "Composite score 0–1 within each category. "
        "🟢 top third · 🟡 middle · 🔴 bottom third. "
        "Cache: 1 hour."
    )

    selected = st.selectbox("Category", list(UNIVERSE.keys()), key="screen_cat")
    color    = CAT_COLORS[selected]
    names    = UNIVERSE[selected]

    with st.spinner(f"Computing {selected} scores..."):
        scores = compute_scores(selected, tuple(names.items()))

    if scores.empty:
        st.warning("No data for this category."); return

    # Score bar + radar side by side (full width)
    col_bar, col_radar = st.columns([1,1])
    with col_bar:
        # Bar chart con colori rank
        df2    = scores[["Score"]].sort_values("Score", ascending=True)
        name_c = "Name" if "Name" in scores.columns else None
        labels = [f"{t} — {scores.loc[t,'Name'][:20]}" if name_c else t for t in df2.index]
        bar_colors = []
        p33 = df2["Score"].quantile(0.33)
        p66 = df2["Score"].quantile(0.66)
        for v in df2["Score"]:
            if v >= p66:   bar_colors.append(RANK_COLORS["high"])
            elif v >= p33: bar_colors.append(RANK_COLORS["mid"])
            else:          bar_colors.append(RANK_COLORS["low"])

        fig_bar = go.Figure(go.Bar(
            y=labels, x=df2["Score"].values, orientation="h",
            marker_color=bar_colors, opacity=0.85,
            text=[f"{v:.2f}" for v in df2["Score"].values],
            textposition="outside", textfont=dict(color=C["text"],size=11),
            hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>"
        ))
        fig_bar.add_vline(x=0.5, line_color=C["muted"], line_dash="dash")
        fig_bar.update_xaxes(range=[0, 1.25])
        apply_layout(fig_bar, f"Composite Score — {selected}",
                     max(340, len(df2)*40+80))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_radar:
        render_radar(scores, selected, color)

    # Data table — una riga per asset, colonne essenziali, font leggibile
    section("Data Table")
    st.caption("Dot color = rank within category: 🟢 top · 🟡 mid · 🔴 bottom")

    col_config = DISPLAY_COLS.get(selected, {})
    # Filtra colonne disponibili
    available_cols = {k: v for k,v in col_config.items() if k in scores.columns}

    if available_cols:
        disp = scores[[c for c in available_cols.keys() if c in scores.columns]].copy()
        rank_cols = {k: v[1] for k,v in available_cols.items() if k != "Name" and v[1] is not None}
        fmt_cols  = {k: v[2] for k,v in available_cols.items() if v[2] is not None}

        # Converti a numerico prima di render
        for col in disp.columns:
            if col != "Name":
                disp[col] = pd.to_numeric(disp[col], errors="coerce")

        render_table(disp, rank_cols=rank_cols, fmt_cols=fmt_cols, height=520)
    else:
        st.dataframe(scores, use_container_width=True)

    # Score legend
    st.markdown(
        f'<div style="margin-top:16px;display:flex;gap:20px;font-size:12px;color:{C["muted"]}">'
        f'<span><span style="color:{RANK_COLORS["high"]}">●</span> Top 33% in category</span>'
        f'<span><span style="color:{RANK_COLORS["mid"]}">●</span> Middle 33%</span>'
        f'<span><span style="color:{RANK_COLORS["low"]}">●</span> Bottom 33%</span>'
        f'</div>',
        unsafe_allow_html=True
    )

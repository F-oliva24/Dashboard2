"""
pages/page_macro.py — Indicatori macroeconomici FRED.
"""
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS
from data import fetch_macro
from ui import kpi, section, apply_layout


def render() -> None:
    st.title("🌍 Macroeconomic Context")
    st.caption("Data from FRED (Federal Reserve). Cache: 24 hours.")

    macro = fetch_macro()
    if macro.empty:
        st.info("Macro data unavailable. Check internet connection.")
        return

    latest = macro.ffill().iloc[-1]

    # KPI row 1
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("Fed Funds Rate",
                  f"{latest.get('Fed Funds Rate', float('nan')):.2f}%", C["blue"],
                  "Tasso di interesse fissato dalla Federal Reserve USA. "
                  "Alti tassi = credito più costoso, freno all'economia. "
                  "Bassi tassi = stimolo, favorevole per azioni e obbligazioni.")
    with k2:
        yc = latest.get("Yield Curve 10-2", float("nan"))
        kpi("Yield Curve 10Y-2Y",
            f"{yc:.2f}%  {'⚠️ Inverted' if yc < 0 else '✅ Normal'}",
            C["red"] if yc < 0 else C["green"],
            "Differenza tra rendimento Treasury USA 10 anni e 2 anni. "
            "Positivo = economia sana. Negativo (invertita) = segnale storico di recessione nei 6-18 mesi.")
    with k3: kpi("VIX",
                  f"{latest.get('VIX', float('nan')):.1f}", C["orange"],
                  "Fear Index: volatilità implicita del mercato USA. "
                  "Sotto 20 = calma. 20-30 = incertezza. Sopra 30 = paura/panico.")
    with k4: kpi("10Y Treasury",
                  f"{latest.get('10Y Treasury', float('nan')):.2f}%", C["teal"],
                  "Rendimento titolo di stato USA 10 anni. "
                  "Tasso risk-free globale di riferimento. Alti rendimenti competono con le azioni.")

    # KPI row 2
    k5,k6,_,_ = st.columns(4)
    with k5: kpi("US CPI",
                  f"{latest.get('US CPI', float('nan')):.1f}", C["purple"],
                  "Indice dei prezzi al consumo USA. Misura l'inflazione. "
                  "CPI in crescita accelerata spinge la Fed ad alzare i tassi.")
    with k6: kpi("EUR/USD",
                  f"{latest.get('EUR/USD', float('nan')):.4f}", C["pink"],
                  "Tasso di cambio Euro/Dollaro. "
                  "EUR/USD alto = euro forte, riduce il valore EUR degli asset USD. "
                  "EUR/USD basso = dollaro forte, aumenta il valore EUR degli asset USD.")

    st.markdown("---")

    # Grafici selezionabili
    selected = st.multiselect("Select indicators to display",
                               options=macro.columns.tolist(),
                               default=macro.columns.tolist())
    if not selected:
        return

    cols = st.columns(2)
    for i, col_name in enumerate(selected):
        with cols[i % 2]:
            s = macro[col_name].dropna().iloc[-10*12:]
            color = CHART_COLORS[i % len(CHART_COLORS)]
            r,g,b = (int(color[j:j+2], 16) for j in (1, 3, 5))
            fig = go.Figure(go.Scatter(
                x=s.index, y=s.values, fill="tozeroy",
                fillcolor=f"rgba({r},{g},{b},0.12)",
                line=dict(color=color, width=2),
                hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"
            ))
            fig.add_annotation(
                text=f"  {s.iloc[-1]:.2f}", x=s.index[-1], y=s.iloc[-1],
                font=dict(size=12, color=color), showarrow=False)
            apply_layout(fig, col_name, 280)
            st.plotly_chart(fig, use_container_width=True)

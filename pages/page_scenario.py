"""
pages/page_scenario.py — Scenario Builder.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, UNIVERSE
from data import fetch_prices, fetch_current_prices, fetch_fx_rates
from portfolio import calc_portfolio
from risk import build_port_returns, calc_risk
from ui import kpi, section, apply_layout, render_risk_charts


def render(budget: float) -> None:
    st.title("🔬 Scenario Builder")
    st.caption("Simulate portfolio changes and compare with your real portfolio.")

    section("Starting Point")
    start_mode = st.radio("Build scenario from:",
                           ["🏦 Current portfolio", "⬜ From scratch"],
                           horizontal=True, key="scenario_mode")

    # Base positions
    base = {}
    if start_mode == "🏦 Current portfolio":
        positions_df = st.session_state.get("positions_df")
        if positions_df is not None and not positions_df.empty:
            for _, row in positions_df.iterrows():
                t = row.get("ticker")
                if t:
                    base[t] = {"ticker": t, "name": str(row.get("yf_name",t)),
                               "qty": float(row.get("qty",0)),
                               "currency": str(row.get("currency","EUR"))}
            st.success(f"Loaded {len(base)} positions from current portfolio.")
        else:
            st.warning("No portfolio loaded. Upload CSV in 'My Portfolio' first.")

    if ("scenario_positions" not in st.session_state or
            st.session_state.get("scenario_mode_prev") != start_mode):
        st.session_state["scenario_positions"] = dict(base)
        st.session_state["scenario_mode_prev"] = start_mode

    scenario = st.session_state["scenario_positions"]

    # Add from universe
    section("Add Assets")
    all_tickers = {t: f"{t} — {n} ({cat})"
                   for cat, items in UNIVERSE.items()
                   for t, n in items.items()}

    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        add_t = st.selectbox("Select from universe", [""] + sorted(all_tickers.keys()),
                              format_func=lambda x: all_tickers.get(x,x) if x else "— Select —",
                              key="scen_add_t")
    with c2:
        add_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=0.5, key="scen_qty")
    with c3:
        add_cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="scen_cur")

    if st.button("➕ Add to Scenario", type="primary") and add_t:
        scenario[add_t] = {"ticker":add_t,"name":all_tickers.get(add_t,add_t),
                            "qty":add_qty,"currency":add_cur}
        st.session_state["scenario_positions"] = scenario
        st.rerun()

    with st.expander("Add custom ticker"):
        cc1,cc2,cc3 = st.columns([2,1,1])
        with cc1: ct = st.text_input("Yahoo ticker",key="ct").upper().strip()
        with cc2: cq = st.number_input("Qty",min_value=0.01,value=1.0,key="cq")
        with cc3: cc = st.selectbox("Currency",["EUR","USD","CHF","GBP"],key="cc")
        if st.button("➕ Add custom",key="btn_ct") and ct:
            scenario[ct] = {"ticker":ct,"name":ct,"qty":cq,"currency":cc}
            st.session_state["scenario_positions"] = scenario
            st.rerun()

    if not scenario:
        st.info("No positions yet."); return

    # Edit positions
    section("Scenario Positions")
    to_remove = []
    cols = st.columns(min(len(scenario), 4))
    for i, (ticker, pos) in enumerate(scenario.items()):
        with cols[i % len(cols)]:
            st.markdown(f'<div class="scenario-card">'
                        f'<b style="color:{CHART_COLORS[i%len(CHART_COLORS)]}">{ticker}</b><br>'
                        f'<small style="color:{C["muted"]}">{pos.get("name","")[:30]}</small>',
                        unsafe_allow_html=True)
            new_qty = st.number_input("Qty", min_value=0.0, value=float(pos.get("qty",1)),
                                       step=0.5, key=f"sq_{ticker}")
            scenario[ticker]["qty"] = new_qty
            if st.button("🗑", key=f"sr_{ticker}"):
                to_remove.append(ticker)
            st.markdown('</div>', unsafe_allow_html=True)

    for t in to_remove:
        del scenario[t]
        st.session_state["scenario_positions"] = scenario
        st.rerun()

    if not scenario:
        return

    # Calcola scenario
    section("Scenario Analysis")
    tickers = tuple(sorted(scenario.keys()))
    curr_px = fetch_current_prices(tickers)
    fx      = fetch_fx_rates()

    scen_rows = [{"ticker":t,"qty":p["qty"],"last_price":curr_px.get(t,0),
                  "currency":p.get("currency","EUR"),"isin":"","yf_name":p.get("name",t),
                  "degiro_price":curr_px.get(t,0),"degiro_currency":p.get("currency","EUR")}
                 for t,p in scenario.items()]
    scen_df    = pd.DataFrame(scen_rows)
    scen_pivot, scen_total = calc_portfolio(scen_df, curr_px, fx)

    k1,k2,k3 = st.columns(3)
    with k1: kpi("Scenario Value",   f"€{scen_total:,.0f}", C["blue"])
    with k2: kpi("Positions",        str(len(scenario)),    C["teal"])
    with k3: kpi("Monthly Budget",   f"€{budget:,.0f}",     C["purple"])

    col_pie, col_alloc = st.columns(2)
    with col_pie:
        vals = pd.to_numeric(scen_pivot["Value (€) YF"], errors="coerce").fillna(0)
        fig_pie = go.Figure(go.Pie(
            labels=scen_pivot.index.tolist(), values=vals.tolist(), hole=0.45,
            textinfo="label+percent", textfont=dict(color=C["text"]),
            marker=dict(colors=CHART_COLORS),
            hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>"
        ))
        fig_pie.add_annotation(text=f"€{scen_total:,.0f}", x=0.5, y=0.5,
            font=dict(size=16,color=C["text"]), showarrow=False)
        apply_layout(fig_pie, "Scenario Allocation", 360)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_alloc:
        section("Budget Split")
        alloc = []
        for t,row in scen_pivot.iterrows():
            w   = float(row["Weight"]) if isinstance(row["Weight"],float) else 0
            b   = budget*w
            cp  = curr_px.get(t)
            cur = scenario.get(t,{}).get("currency","EUR")
            pe  = cp*fx.get(cur,1.0) if cp else None
            qs  = b/pe if pe else None
            alloc.append({"Ticker":t,"Weight":f"{w:.1%}","Budget":f"€{b:.2f}",
                          "Price(€)":f"€{pe:.2f}" if pe else "N/A",
                          "Units":f"{qs:.3f}" if qs else "N/A"})
        adf = pd.DataFrame(alloc)
        adf.loc[len(adf)] = ["TOTAL","100%",f"€{budget:.2f}","",""]
        st.dataframe(adf.set_index("Ticker"), use_container_width=True)

    # Risk
    prices_scen = fetch_prices(tickers, "3y")
    vw = {t: float(scen_pivot.loc[t,"Value (€) YF"])
          for t in tickers if t in scen_pivot.index and pd.notna(scen_pivot.loc[t,"Value (€) YF"])}
    port_ret = build_port_returns(prices_scen, vw)
    if port_ret is not None:
        render_risk_charts(port_ret, scen_total)

        # Comparison vs real
        positions_df = st.session_state.get("positions_df")
        if positions_df is not None and not positions_df.empty and start_mode == "🏦 Current portfolio":
            section("Scenario vs Current Portfolio")
            real_t   = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
            real_px  = fetch_current_prices(real_t)
            real_piv, real_total = calc_portfolio(positions_df, real_px, fx)
            real_prices = fetch_prices(real_t, "3y")
            real_vw  = {t: float(real_piv.loc[t,"Value (€) YF"])
                        for t in real_t if t in real_piv.index and pd.notna(real_piv.loc[t,"Value (€) YF"])}
            real_ret = build_port_returns(real_prices, real_vw)
            if real_ret is not None:
                rr = calc_risk(real_ret, real_total, 0.95, 1)
                rs = calc_risk(port_ret, scen_total, 0.95, 1)
                comp = pd.DataFrame({
                    "Metric":   ["Annual Return","Volatility","Sharpe","Max Drawdown","VaR 95% 1d"],
                    "Current":  [f"{rr['annual_return']:+.2%}",f"{rr['volatility']:.2%}",
                                  f"{rr['sharpe']:.2f}",f"{rr['max_drawdown']:.2%}",
                                  f"€{rr['var_hist_eur']:,.0f}"],
                    "Scenario": [f"{rs['annual_return']:+.2%}",f"{rs['volatility']:.2%}",
                                  f"{rs['sharpe']:.2f}",f"{rs['max_drawdown']:.2%}",
                                  f"€{rs['var_hist_eur']:,.0f}"],
                }).set_index("Metric")
                st.dataframe(comp, use_container_width=True)

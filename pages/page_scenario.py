"""
pages/page_scenario.py — Scenario Builder (from current portfolio only).
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, UNIVERSE
from data import fetch_prices, fetch_current_prices, fetch_fx_rates
from portfolio import calc_portfolio, load_cached_portfolio
from risk import build_port_returns, calc_risk
from ui import kpi, section, apply_layout, render_risk_charts, render_table


def render(budget: float) -> None:
    st.title("🔬 Scenario Builder")
    st.caption("Simulate changes to your current portfolio. "
               "Add or remove positions and see the impact on risk and allocation.")

    positions_df = st.session_state.get("positions_df") or load_cached_portfolio()
    if positions_df is None or positions_df.empty:
        st.markdown('<div class="upload-hint">📂 Upload DEGIRO CSV in My Portfolio first.</div>',
                    unsafe_allow_html=True)
        return

    # Init scenario from current portfolio
    if "scenario_positions" not in st.session_state:
        base = {}
        for _, row in positions_df.iterrows():
            t = row.get("ticker")
            if t:
                base[t] = {"ticker":t, "name":str(row.get("yf_name",t)),
                            "qty":float(row.get("qty",0)),
                            "currency":str(row.get("currency","EUR"))}
        st.session_state["scenario_positions"] = base

    scenario = st.session_state["scenario_positions"]

    # ---- ADD ASSETS ----
    section("Add Assets to Scenario")
    all_tickers = {t: f"{t} — {n} ({cat})"
                   for cat, items in UNIVERSE.items()
                   for t, n in items.items()}

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        add_t = st.selectbox("Select from universe", [""] + sorted(all_tickers.keys()),
                              format_func=lambda x: all_tickers.get(x,x) if x else "— Select asset —",
                              key="scen_add_t")
    with c2:
        add_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=0.5, key="scen_qty")
    with c3:
        add_cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="scen_cur")

    c_add, c_reset = st.columns([1,1])
    with c_add:
        if st.button("➕ Add to Scenario", type="primary") and add_t:
            scenario[add_t] = {"ticker":add_t, "name":all_tickers.get(add_t,add_t),
                                "qty":add_qty, "currency":add_cur}
            st.session_state["scenario_positions"] = scenario
            st.rerun()
    with c_reset:
        if st.button("↩️ Reset to Current Portfolio"):
            st.session_state.pop("scenario_positions", None)
            st.rerun()

    with st.expander("Add custom ticker (not in universe)"):
        cc1,cc2,cc3 = st.columns([2,1,1])
        with cc1: ct = st.text_input("Yahoo ticker", key="ct_scen").upper().strip()
        with cc2: cq = st.number_input("Qty", min_value=0.01, value=1.0, key="cq_scen")
        with cc3: cc = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="cc_scen")
        if st.button("➕ Add custom", key="btn_ct_scen") and ct:
            scenario[ct] = {"ticker":ct,"name":ct,"qty":cq,"currency":cc}
            st.session_state["scenario_positions"] = scenario
            st.rerun()

    if not scenario:
        st.info("No positions in scenario."); return

    # ---- EDIT / REMOVE ----
    section("Scenario Positions")
    to_remove = []
    n_cols = min(len(scenario), 4)
    cols   = st.columns(n_cols)
    for i, (ticker, pos) in enumerate(scenario.items()):
        with cols[i % n_cols]:
            hex_c = CHART_COLORS[i%len(CHART_COLORS)]
            st.markdown(
                f'<div class="top3-card">'
                f'<div style="font-size:13px;font-weight:700;color:{hex_c}">{ticker}</div>'
                f'<div style="font-size:11px;color:{C["muted"]};margin:2px 0 8px">'
                f'{pos.get("name","")[:28]}</div>',
                unsafe_allow_html=True
            )
            new_qty = st.number_input("Qty", min_value=0.0, value=float(pos.get("qty",1)),
                                       step=0.5, key=f"sq_{ticker}")
            scenario[ticker]["qty"] = new_qty
            if st.button("🗑 Remove", key=f"sr_{ticker}"):
                to_remove.append(ticker)
            st.markdown('</div>', unsafe_allow_html=True)

    for t in to_remove:
        del scenario[t]
        st.session_state["scenario_positions"] = scenario
        st.rerun()

    if not scenario:
        return

    # ---- COMPUTE ----
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

    # KPI comparison
    real_tickers = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
    real_curr    = fetch_current_prices(real_tickers)
    real_pivot, real_total = calc_portfolio(positions_df, real_curr, fx)

    section("Scenario vs Current Portfolio")
    col_s, col_r = st.columns(2)
    with col_s:
        st.markdown(f'<div style="color:{C["blue"]};font-size:11px;font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">'
                    f'Scenario</div>', unsafe_allow_html=True)
        kpi("Value", f"€{scen_total:,.0f}", C["blue"])
        kpi("Positions", str(len(scenario)), C["teal"])
    with col_r:
        st.markdown(f'<div style="color:{C["muted"]};font-size:11px;font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">'
                    f'Current</div>', unsafe_allow_html=True)
        kpi("Value", f"€{real_total:,.0f}", C["muted"])
        kpi("Positions", str(len(real_tickers)), C["muted"])

    # Allocation pies side by side
    col_p1, col_p2 = st.columns(2)
    for (pivot_data, total_v, title, col) in [
        (scen_pivot, scen_total, "Scenario Allocation", col_p1),
        (real_pivot, real_total, "Current Allocation",  col_p2),
    ]:
        with col:
            vals = pd.to_numeric(pivot_data["Value (€) YF"], errors="coerce").fillna(0)
            fig  = go.Figure(go.Pie(
                labels=pivot_data.index.tolist(), values=vals.tolist(), hole=0.5,
                textinfo="label+percent", textfont=dict(color=C["text"],size=10),
                marker=dict(colors=CHART_COLORS,line=dict(color=C["bg"],width=2)),
                hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>"
            ))
            fig.add_annotation(text=f"€{total_v:,.0f}", x=0.5, y=0.5,
                font=dict(size=14,color=C["text"]), showarrow=False)
            apply_layout(fig, title, 320)
            st.plotly_chart(fig, use_container_width=True)

    # Risk comparison
    prices_scen = fetch_prices(tickers, "3y")
    prices_real = fetch_prices(real_tickers, "3y")

    vw_scen = {t: float(scen_pivot.loc[t,"Value (€) YF"])
               for t in tickers if t in scen_pivot.index and pd.notna(scen_pivot.loc[t,"Value (€) YF"])}
    vw_real = {t: float(real_pivot.loc[t,"Value (€) YF"])
               for t in real_tickers if t in real_pivot.index and pd.notna(real_pivot.loc[t,"Value (€) YF"])}

    ret_scen = build_port_returns(prices_scen, vw_scen)
    ret_real = build_port_returns(prices_real, vw_real)

    if ret_scen is not None and ret_real is not None:
        rs = calc_risk(ret_scen, scen_total, 0.95, 1)
        rr = calc_risk(ret_real, real_total, 0.95, 1)

        comp = pd.DataFrame({
            "Metric":   ["Annual Return","Volatility","Sharpe","Max Drawdown",
                         "VaR 95% 1d","VaR 99% 1d"],
            "Scenario": [f"{rs['annual_return']:+.2%}", f"{rs['volatility']:.2%}",
                          f"{rs['sharpe']:.2f}",        f"{rs['max_drawdown']:.2%}",
                          f"€{rs['var_hist_eur']:,.0f}", f"€{calc_risk(ret_scen,scen_total,.99,1)['var_hist_eur']:,.0f}"],
            "Current":  [f"{rr['annual_return']:+.2%}", f"{rr['volatility']:.2%}",
                          f"{rr['sharpe']:.2f}",        f"{rr['max_drawdown']:.2%}",
                          f"€{rr['var_hist_eur']:,.0f}", f"€{calc_risk(ret_real,real_total,.99,1)['var_hist_eur']:,.0f}"],
        }).set_index("Metric")
        render_table(comp)

        # Cumulative return comparison
        cum_s = rs["cumulative_returns"]
        cum_r = rr["cumulative_returns"]
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(
            x=cum_s.index, y=(cum_s-1)*100, name="Scenario",
            line=dict(color=C["blue"], width=2),
            hovertemplate="%{x|%d %b %Y}: %{y:.2f}%<extra></extra>"
        ))
        fig_c.add_trace(go.Scatter(
            x=cum_r.index, y=(cum_r-1)*100, name="Current",
            line=dict(color=C["muted"], width=1.5, dash="dash"),
            hovertemplate="%{x|%d %b %Y}: %{y:.2f}%<extra></extra>"
        ))
        apply_layout(fig_c, "Cumulative Return: Scenario vs Current", 360)
        st.plotly_chart(fig_c, use_container_width=True)

    # Budget allocation per scenario
    section(f"Monthly Budget Allocation — €{budget:,.0f}")
    alloc_rows = []
    for ticker, row in scen_pivot.iterrows():
        w     = float(row["Weight"]) if isinstance(row["Weight"],float) else 0
        bud   = budget * w
        cp    = curr_px.get(ticker)
        cur   = scenario.get(ticker,{}).get("currency","EUR")
        p_eur = cp*fx.get(cur,1.0) if cp else None
        alloc_rows.append({
            "Weight":    f"{w:.1%}",
            "Budget":    f"€{bud:.2f}",
            "Price (€)": f"€{p_eur:.2f}" if p_eur else "—",
            "Units":     f"{bud/p_eur:.3f}" if p_eur else "—",
        })
    alloc_df = pd.DataFrame(alloc_rows, index=scen_pivot.index)
    alloc_df.loc["TOTAL"] = ["100%", f"€{budget:.2f}", "", ""]
    render_table(alloc_df)

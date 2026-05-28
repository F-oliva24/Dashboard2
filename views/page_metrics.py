"""
pages/page_metrics.py — Layer Metrics.
Portfolio level + asset level. Struttura aperta per nuovi dati futuri.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, ISIN_MAP
from data import (fetch_current_prices, fetch_fx_rates, fetch_prices,
                  fetch_fundamentals, fetch_dividends, fetch_implicit_yield)
from portfolio import (calc_portfolio, load_buy_prices, load_commissions,
                       load_cached_portfolio)
from risk import build_port_returns, calc_risk
from ui import kpi, section, apply_layout, render_table


def render(budget: float) -> None:
    st.title("📊 Metrics")
    st.caption("Portfolio-level and asset-level metrics. "
               "New data sources (dividends, earnings) integrate automatically when available.")

    positions_df = st.session_state.get("positions_df") or load_cached_portfolio()
    if positions_df is None or positions_df.empty:
        st.markdown('<div class="upload-hint">📂 Upload DEGIRO CSV in My Portfolio first.</div>',
                    unsafe_allow_html=True)
        return

    valid_tickers = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
    with st.spinner("Loading metrics data..."):
        curr_px     = fetch_current_prices(valid_tickers)
        fx_rates    = fetch_fx_rates()
        buy_prices  = st.session_state.get("buy_prices",  load_buy_prices())
        commissions = st.session_state.get("commissions", load_commissions())
        prices_ptf  = fetch_prices(valid_tickers, "3y")
        fund        = fetch_fundamentals(valid_tickers)
        divs        = fetch_dividends(valid_tickers)

    pivot, total_value = calc_portfolio(positions_df, curr_px, fx_rates,
                                         buy_prices, commissions)
    total_cost = pd.to_numeric(pivot["Cost (€)"], errors="coerce").sum()
    total_pl   = pd.to_numeric(pivot["P&L (€)"],  errors="coerce").sum()

    value_weights = {t: float(pivot.loc[t,"Value (€) YF"])
                     for t in valid_tickers
                     if t in pivot.index and pd.notna(pivot.loc[t,"Value (€) YF"])}
    port_ret = build_port_returns(prices_ptf, value_weights)

    # ================================================================
    #  PORTFOLIO LEVEL
    # ================================================================
    section("Portfolio Level")

    # Performance
    if port_ret is not None and len(port_ret) > 20:
        r = calc_risk(port_ret, total_value, 0.95, 1)
        col1,col2,col3,col4,col5,col6 = st.columns(6)
        with col1: kpi("Total Value",    f"€{total_value:,.0f}", C["blue"])
        with col2: kpi("Total P&L",
                        f"€{total_pl:+,.0f}",
                        C["green"] if total_pl>=0 else C["red"],
                        "P&L non realizzato netto commissioni.")
        with col3: kpi("P&L %",
                        f"{total_pl/total_cost:+.2%}" if total_cost>0 else "—",
                        C["green"] if total_pl>=0 else C["red"])
        with col4: kpi("Annual Return",  f"{r['annual_return']:+.1%}", C["teal"],
                        "CAGR su 3 anni di storia prezzi.")
        with col5: kpi("Sharpe",         f"{r['sharpe']:.2f}", C["orange"],
                        "Rendimento per unità di rischio.")
        with col6: kpi("Max Drawdown",   f"{r['max_drawdown']:.1%}", C["red"],
                        "Perdita massima dal picco nel periodo analizzato.")

        # Rendimenti per periodo
        section("Returns by Period")
        periods = {
            "1M": 21, "3M": 63, "6M": 126, "1Y": 252, "2Y": 504, "3Y": 756
        }
        ret_cols = st.columns(len(periods))
        for (label, days), col in zip(periods.items(), ret_cols):
            if len(port_ret) > days:
                ret_period = (1+port_ret.iloc[-days:]).prod() - 1
                col.metric(label, f"{ret_period:+.2%}")

    # Dividendi portafoglio (solo stock distributrici)
    section("Income & Dividends")
    div_rows = []
    total_div_annual = 0.0
    for ticker in valid_tickers:
        isin_rows = positions_df[positions_df["ticker"]==ticker]
        isin_val  = str(isin_rows["isin"].values[0]) if not isin_rows.empty else ""
        is_acc    = ISIN_MAP.get(isin_val,{}).get("accumulation", False)
        qty       = float(isin_rows["qty"].values[0]) if not isin_rows.empty else 0
        cp        = curr_px.get(ticker, 0)
        cur       = ISIN_MAP.get(isin_val,{}).get("currency","EUR")
        fx        = fx_rates.get(cur, 1.0)
        val_eur   = qty * cp * fx if cp else 0

        if is_acc:
            # Yield implicito
            impl_y = fetch_implicit_yield(ticker)
            if impl_y:
                div_annual = val_eur * impl_y
                total_div_annual += div_annual
                div_rows.append({
                    "Type":          "Accumulation (implicit)",
                    "Yield":         f"~{impl_y:.2%}",
                    "Annual (€)":    f"€{div_annual:,.2f}",
                    "Monthly (€)":   f"€{div_annual/12:,.2f}",
                    "Note":          "Reinvested in NAV — not distributed",
                })
            else:
                div_rows.append({
                    "Type":        "Accumulation (implicit)",
                    "Yield":       "N/A",
                    "Annual (€)":  "—",
                    "Monthly (€)": "—",
                    "Note":        "Reinvested in NAV",
                })
        else:
            # Dividendo reale da yfinance
            div_series = divs.get(ticker, pd.Series(dtype=float))
            if div_series is not None and len(div_series) > 0:
                last_12m = div_series.last("365D").sum() if not div_series.empty else 0
                div_annual = last_12m * qty * fx
                div_yield  = last_12m / cp if cp else 0
                total_div_annual += div_annual
                div_rows.append({
                    "Type":        "Distributing",
                    "Yield":       f"{div_yield:.2%}",
                    "Annual (€)":  f"€{div_annual:,.2f}",
                    "Monthly (€)": f"€{div_annual/12:,.2f}",
                    "Note":        f"Last 12M: {last_12m:.4f} {cur}/share",
                })
            else:
                div_rows.append({
                    "Type":        "Distributing",
                    "Yield":       "—",
                    "Annual (€)":  "—",
                    "Monthly (€)": "—",
                    "Note":        "No dividend history",
                })

    if div_rows:
        div_df = pd.DataFrame(div_rows, index=[t for t in valid_tickers])
        div_df.index.name = "Ticker"
        render_table(div_df)
        if total_div_annual > 0:
            st.markdown(
                f'<div style="margin-top:12px;padding:14px 20px;background:{C["card2"]};'
                f'border:1px solid {C["border"]};border-radius:10px">'
                f'<span style="color:{C["muted"]};font-size:11px;text-transform:uppercase;'
                f'letter-spacing:.08em">Total Annual Income (explicit + implicit)</span><br>'
                f'<span style="font-size:22px;font-weight:800;color:{C["green"]}">'
                f'€{total_div_annual:,.2f}</span>'
                f'<span style="color:{C["muted"]};font-size:13px;margin-left:12px">'
                f'≈ €{total_div_annual/12:,.2f}/month</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ================================================================
    #  ASSET LEVEL
    # ================================================================
    section("Asset Level Metrics")

    asset_rows = {}
    for ticker in valid_tickers:
        if ticker not in prices_ptf.columns:
            continue
        s   = prices_ptf[ticker].dropna()
        ret = s.pct_change().dropna()
        if len(ret) < 20:
            continue

        r_asset  = calc_risk(ret, 1.0, 0.95, 1)  # normalized
        isin_rows = positions_df[positions_df["ticker"]==ticker]
        qty       = float(isin_rows["qty"].values[0]) if not isin_rows.empty else 0
        cp        = curr_px.get(ticker)
        isin_val  = str(isin_rows["isin"].values[0]) if not isin_rows.empty else ""
        cur       = ISIN_MAP.get(isin_val,{}).get("currency","EUR")
        fx        = fx_rates.get(cur,1.0)
        val_eur   = qty*cp*fx if cp else 0
        weight    = val_eur/total_value if total_value>0 else 0

        # Fondamentali se disponibili
        f_row = fund.loc[ticker] if ticker in fund.index else pd.Series(dtype=float)

        asset_rows[ticker] = {
            "Weight":          f"{weight:.1%}",
            "Return 1Y":       f"{r_asset['annual_return']:+.1%}",
            "Volatility":      f"{r_asset['volatility']:.1%}",
            "Sharpe":          f"{r_asset['sharpe']:.2f}" if pd.notna(r_asset['sharpe']) else "—",
            "Max DD":          f"{r_asset['max_drawdown']:.1%}",
            "VaR 95% 1d":      f"{r_asset['var_hist_pct']:.2%}",
            # Fondamentali (None-safe)
            "Beta":            f"{f_row.get('Beta'):.2f}" if pd.notna(f_row.get('Beta')) else "—",
            "Forward P/E":     f"{f_row.get('Forward P/E'):.1f}" if pd.notna(f_row.get('Forward P/E')) else "—",
            "Div Yield":       f"{f_row.get('Div Yield (TTM)'):.2%}" if pd.notna(f_row.get('Div Yield (TTM)')) else "—",
            "Revenue Growth":  f"{f_row.get('Revenue Growth'):.1%}" if pd.notna(f_row.get('Revenue Growth')) else "—",
        }

    if asset_rows:
        asset_df = pd.DataFrame(asset_rows).T
        asset_df.index.name = "Ticker"
        render_table(
            asset_df,
            rank_cols={
                "Return 1Y":  True,
                "Sharpe":     True,
                "Max DD":     False,
                "Volatility": False,
            },
            fmt_cols={}
        )

    # Contribution to portfolio risk
    if port_ret is not None and len(valid_t := [t for t in valid_tickers if t in prices_ptf.columns]) > 1:
        section("Risk Contribution per Asset")
        ret_df  = prices_ptf[valid_t].pct_change().dropna()
        w_arr   = np.array([value_weights.get(t,0) for t in valid_t])
        w_arr   = w_arr / w_arr.sum() if w_arr.sum()>0 else w_arr
        cov     = ret_df.cov().values * 252
        port_vol= np.sqrt(w_arr @ cov @ w_arr)
        if port_vol > 0:
            marg    = cov @ w_arr / port_vol
            contrib = w_arr * marg
            pct_c   = contrib / port_vol

            fig_rc = go.Figure(go.Bar(
                x=valid_t,
                y=(pct_c * 100).tolist(),
                marker_color=[CHART_COLORS[i%len(CHART_COLORS)] for i in range(len(valid_t))],
                text=[f"{v:.1f}%" for v in pct_c*100],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Risk contrib: %{y:.2f}%<extra></extra>"
            ))
            apply_layout(fig_rc, "Risk Contribution (% of total portfolio risk)", 300)
            st.plotly_chart(fig_rc, use_container_width=True)

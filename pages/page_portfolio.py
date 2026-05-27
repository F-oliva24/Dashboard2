"""
pages/page_portfolio.py — Pagina My Portfolio.
Upload CSV DEGIRO → metriche, P&L, VaR, allocazione mensile.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from config import C, CHART_COLORS, ISIN_MAP
from data import fetch_current_prices, fetch_fx_rates, fetch_prices
from portfolio import (parse_degiro_csv, calc_portfolio,
                       load_buy_prices, save_buy_prices,
                       load_commissions, save_commissions,
                       save_cached_portfolio, commission_rate)
from risk import build_port_returns
from ui import kpi, section, apply_layout, render_risk_charts


def render(is_admin: bool, budget: float) -> None:
    st.title("💼 My Portfolio")

    # Refresh buttons
    c1, c2, _ = st.columns([1, 1, 5])
    with c1:
        if st.button("🔄 Prices", type="primary"):
            st.cache_data.clear(); st.rerun()
    with c2:
        if st.button("🔄 All"):
            st.cache_data.clear(); st.rerun()

    # CSV Upload
    section("Upload DEGIRO Portfolio CSV")
    if is_admin:
        uploaded = st.file_uploader(
            "Drag & drop your DEGIRO CSV export here", type=["csv"],
            key="ptf_csv", help="DEGIRO → Portfolio → Export → CSV"
        )
        if uploaded:
            positions_df, unmapped = parse_degiro_csv(uploaded)
            if not positions_df.empty:
                st.session_state["positions_df"] = positions_df
                save_cached_portfolio(positions_df)
            if unmapped:
                st.warning(f"Unknown ISINs — map manually: {unmapped}")
                for isin in unmapped:
                    c1, c2 = st.columns(2)
                    with c1: t = st.text_input(f"Yahoo ticker for {isin}", key=f"map_{isin}")
                    with c2: cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key=f"cur_{isin}")
                    if t:
                        ISIN_MAP[isin] = {"ticker": t.upper(), "currency": cur, "name": isin}
    else:
        st.info("👁 Read-only — ask admin to upload the latest CSV.")

    # Carica posizioni
    positions_df = st.session_state.get("positions_df")
    if positions_df is None:
        from portfolio import load_cached_portfolio
        positions_df = load_cached_portfolio()
        if positions_df is not None:
            st.session_state["positions_df"] = positions_df

    if positions_df is None or positions_df.empty:
        st.markdown('<div class="upload-hint">📂 Upload your DEGIRO CSV to see portfolio metrics</div>',
                    unsafe_allow_html=True)
        return

    valid_tickers = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
    if not valid_tickers:
        st.warning("No valid tickers. Check ISIN mapping."); return

    with st.spinner("Loading prices..."):
        current_prices = fetch_current_prices(valid_tickers)
        fx_rates       = fetch_fx_rates()

    # Buy prices
    if "buy_prices" not in st.session_state:
        st.session_state["buy_prices"] = load_buy_prices()
    buy_prices = st.session_state["buy_prices"]

    if is_admin:
        section("Buy Prices (Manual Override)")
        st.caption("Enter your actual average buy price. Saved automatically. Used for P&L.")
        has_missing = any(
            str(row.get("isin","")) not in buy_prices or buy_prices.get(str(row.get("isin","")),0)==0
            for _, row in positions_df.iterrows()
        )
        if has_missing:
            st.warning("⚠️ Some positions missing a manual buy price — using DEGIRO price as fallback.")
        bp_cols = st.columns(min(len(positions_df), 3))
        for i, (_, pos) in enumerate(positions_df.iterrows()):
            isin    = str(pos.get("isin",""))
            name    = str(pos.get("yf_name", pos.get("name","")))[:25]
            cur     = str(pos.get("degiro_currency", pos.get("currency","EUR")))
            curr_bp = float(buy_prices.get(isin, 0.0))
            with bp_cols[i % len(bp_cols)]:
                new_bp = st.number_input(f"{name} ({cur})", min_value=0.0,
                                          value=curr_bp, step=0.01,
                                          format="%.4f", key=f"bp_{isin}")
                if new_bp != curr_bp:
                    buy_prices[isin] = new_bp
                    st.session_state["buy_prices"] = buy_prices
                    save_buy_prices(buy_prices)

    # Commissions
    if "commissions" not in st.session_state:
        st.session_state["commissions"] = load_commissions()
    commissions = st.session_state["commissions"]

    if is_admin:
        section("Number of Transactions (for commission calculation)")
        st.caption("Each transaction: €1 (EUR) or €3 (other currencies).")
        tx_cols = st.columns(min(len(positions_df), 3))
        for i, (_, pos) in enumerate(positions_df.iterrows()):
            isin       = str(pos.get("isin",""))
            name       = str(pos.get("yf_name", pos.get("name","")))[:25]
            mapped_cur = ISIN_MAP.get(isin, {}).get("currency", pos.get("currency","EUR"))
            rate       = 1 if mapped_cur == "EUR" else 3
            curr_tx    = int(commissions.get(isin, 1))
            with tx_cols[i % len(tx_cols)]:
                new_tx = st.number_input(f"{name} (€{rate}/tx)", min_value=1,
                                          max_value=100, value=curr_tx, step=1,
                                          key=f"tx_{isin}")
                if new_tx != curr_tx:
                    commissions[isin] = new_tx
                    st.session_state["commissions"] = commissions
                    save_commissions(commissions)

    # Calcola portafoglio
    pivot, total_value = calc_portfolio(positions_df, current_prices, fx_rates,
                                        buy_prices, commissions)
    total_cost        = pd.to_numeric(pivot["Cost (€)"],       errors="coerce").sum()
    total_commissions = pd.to_numeric(pivot["Commission (€)"], errors="coerce").sum()
    total_pl          = pd.to_numeric(pivot["P&L (€)"],        errors="coerce").sum()
    total_pl_pct      = total_pl / total_cost if total_cost > 0 else 0

    # KPI
    section("Overview")
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Total Value", f"€{total_value:,.0f}", C["blue"],
                  "Valore corrente totale del portafoglio in EUR ai tassi di cambio attuali.")
    with k2: kpi("P&L (net commissions)",
                  f"€{total_pl:+,.0f} ({total_pl_pct:+.1%})",
                  C["green"] if total_pl >= 0 else C["red"],
                  "Profitto/perdita non realizzata rispetto al prezzo di acquisto, al netto delle commissioni.")
    with k3: kpi("Total Commissions", f"€{total_commissions:,.2f}", C["muted"],
                  "Totale commissioni pagate: €1/transazione EUR, €3/transazione altre valute.")
    with k4: kpi("Monthly Budget", f"€{budget:,.0f}", C["purple"],
                  "Budget mensile per nuovi acquisti. Modificabile dalla sidebar.")

    # Tabella posizioni
    section("Positions")
    disp = pivot.drop(columns=["_val_orig","_pl_orig","Cost (€)","P&L (€)","Commission (€)"],
                       errors="ignore").copy()
    disp["P&L (%)"] = disp["P&L (%)"].apply(lambda x: f"{x:+.2%}" if pd.notna(x) else "N/A")
    disp["Weight"]  = disp["Weight"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
    for col in ["Value (€) YF", "Value (€) DEGIRO"]:
        if col in disp.columns:
            disp[col] = disp[col].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
    st.dataframe(disp, use_container_width=True)

    # Allocation
    section("Allocation & Monthly Budget")
    col_pie, col_alloc = st.columns(2)
    with col_pie:
        vals = pd.to_numeric(pivot["Value (€) YF"], errors="coerce").fillna(0)
        fig_pie = go.Figure(go.Pie(
            labels=pivot.index.tolist(), values=vals.tolist(), hole=0.45,
            textinfo="label+percent", textfont=dict(color=C["text"]),
            marker=dict(colors=CHART_COLORS),
            hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>"
        ))
        fig_pie.add_annotation(text=f"€{total_value:,.0f}", x=0.5, y=0.5,
            font=dict(size=16, color=C["text"]), showarrow=False)
        apply_layout(fig_pie, "Portfolio Allocation", 360)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_alloc:
        section("Budget Split")
        alloc_rows = []
        for ticker, row in pivot.iterrows():
            w       = float(row["Weight"]) if isinstance(row["Weight"], float) else 0
            bud     = budget * w
            cp      = current_prices.get(ticker)
            cur     = str(row.get("Currency","EUR"))
            fx      = fx_rates.get(cur, 1.0)
            p_eur   = cp * fx if cp else None
            qty_sug = bud / p_eur if p_eur else None
            alloc_rows.append({
                "Ticker":       ticker,
                "Weight":       f"{w:.1%}",
                "Budget (€)":   f"€{bud:.2f}",
                "Price (€)":    f"€{p_eur:.2f}" if p_eur else "N/A",
                "Units to buy": f"{qty_sug:.3f}" if qty_sug else "N/A",
            })
        alloc_df = pd.DataFrame(alloc_rows)
        alloc_df.loc[len(alloc_df)] = ["TOTAL","100%",f"€{budget:.2f}","",""]
        st.dataframe(alloc_df.set_index("Ticker"), use_container_width=True)

    # P&L bar
    pl_vals = pd.to_numeric(pivot["P&L (€)"], errors="coerce")
    pl_cols = [C["green"] if (pd.notna(v) and v>=0) else C["red"] for v in pl_vals]
    fig_pl  = go.Figure(go.Bar(
        x=pivot.index.tolist(), y=pl_vals.tolist(), marker_color=pl_cols,
        text=[f"€{v:+,.0f}" if pd.notna(v) else "N/A" for v in pl_vals],
        textposition="outside", textfont=dict(color=C["text"]),
        hovertemplate="<b>%{x}</b><br>P&L: €%{y:+,.2f}<extra></extra>"
    ))
    fig_pl.add_hline(y=0, line_color=C["muted"], line_width=1)
    apply_layout(fig_pl, f"Unrealised P&L  |  Total: €{total_pl:+,.0f}", 340)
    st.plotly_chart(fig_pl, use_container_width=True)

    # Risk
    section("Risk Analysis")
    prices_ptf = fetch_prices(valid_tickers, "3y")
    value_weights = {t: float(pivot.loc[t,"Value (€) YF"])
                     for t in valid_tickers
                     if t in pivot.index and pd.notna(pivot.loc[t,"Value (€) YF"])}
    port_ret = build_port_returns(prices_ptf, value_weights)
    if port_ret is not None:
        render_risk_charts(port_ret, total_value)
        # Correlation
        valid_t = [t for t in valid_tickers if t in prices_ptf.columns]
        if len(valid_t) > 1:
            corr = prices_ptf[valid_t].pct_change().dropna().corr()
            fig_corr = go.Figure(go.Heatmap(
                z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                colorscale=[[0,C["red"]],[0.5,"#111"],[1,C["green"]]],
                zmin=-1, zmax=1,
                text=[[f"{v:.2f}" for v in row] for row in corr.values],
                texttemplate="%{text}", textfont=dict(color=C["text"]),
                hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>"
            ))
            apply_layout(fig_corr, "Correlation Matrix", 380)
            st.plotly_chart(fig_corr, use_container_width=True)

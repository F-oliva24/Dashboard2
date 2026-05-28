
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, ISIN_MAP, UNIVERSE, SNAPSHOTS_FILE
from data import fetch_current_prices, fetch_fx_rates, fetch_prices, fetch_implicit_yield
from portfolio import (parse_degiro_csv, calc_portfolio,
                       load_buy_prices, save_buy_prices,
                       load_commissions, save_commissions,
                       save_cached_portfolio)
from risk import build_port_returns
from scoring import compute_scores
from ui import kpi, section, apply_layout, render_risk_charts, render_top3_cards, render_table


# ------------------------------------------------------------------ #
#  SNAPSHOT
# ------------------------------------------------------------------ #

def _load_snapshots() -> list:
    if SNAPSHOTS_FILE.exists():
        try:
            with open(SNAPSHOTS_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

def _save_snapshot(total_value: float, pl_eur: float, pl_pct: float) -> None:
    try:
        snaps = _load_snapshots()
        today = datetime.now().strftime("%Y-%m-%d")
        snaps = [s for s in snaps if s.get("date") != today]
        snaps.append({"date": today,
                       "value": round(total_value, 2),
                       "pl":    round(pl_eur, 2),
                       "pl_pct": round(pl_pct, 4)})
        snaps.sort(key=lambda x: x["date"])
        with open(SNAPSHOTS_FILE, "w") as f:
            json.dump(snaps, f, indent=2)
    except:
        pass  # Mai crashare per uno snapshot


# ------------------------------------------------------------------ #
#  SAFE COLUMN ACCESS
# ------------------------------------------------------------------ #

def _col(row, *names, default=""):
    """Accede a una colonna di una riga pandas in modo robusto."""
    for name in names:
        try:
            val = row[name]
            if pd.notna(val):
                return val
        except (KeyError, TypeError):
            pass
    return default


# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #

def render(is_admin: bool, budget: float) -> None:
    st.title("💼 My Portfolio")

    c1, c2, _ = st.columns([1, 1, 5])
    with c1:
        if st.button("🔄 Prices", type="primary"):
            st.cache_data.clear(); st.rerun()
    with c2:
        if st.button("🔄 All"):
            st.cache_data.clear(); st.rerun()

    # ---- CSV UPLOAD ----
    section("Upload DEGIRO CSV")
    if is_admin:
        uploaded = st.file_uploader(
            "DEGIRO → Portfolio → Export → CSV",
            type=["csv"], key="ptf_csv"
        )
        if uploaded is not None:
            try:
                positions_new, unmapped = parse_degiro_csv(uploaded)
                if not positions_new.empty:
                    st.session_state["positions_df"] = positions_new
                    save_cached_portfolio(positions_new)
                    st.success(f"✅ Loaded {len(positions_new)} positions")
                else:
                    st.error("Could not parse CSV. Check format.")
                if unmapped:
                    st.warning(f"Unknown ISINs: {unmapped}")
                    for isin in unmapped:
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            t = st.text_input(f"Yahoo ticker for {isin}", key=f"map_{isin}")
                        with cc2:
                            cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key=f"cur_{isin}")
                        if t:
                            ISIN_MAP[isin] = {"ticker": t.upper(), "currency": cur,
                                              "name": isin, "accumulation": True}
            except Exception as e:
                st.error(f"Upload error: {e}")
    else:
        st.info("👁 Read-only — admin uploads CSV.")

    # ---- CARICA POSIZIONI (solo da session_state, no file cache) ----
    positions_df = st.session_state.get("positions_df")

    # Prova a caricare dal file solo se non in session e il file esiste
    if positions_df is None:
        cache_file = Path("last_portfolio.json")
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    raw = json.load(f)
                if isinstance(raw, list) and raw:
                    positions_df = pd.DataFrame(raw)
                    # Valida colonne minime
                    if "ticker" not in positions_df.columns:
                        positions_df = None
                    else:
                        st.session_state["positions_df"] = positions_df
            except:
                positions_df = None

    if positions_df is None or positions_df.empty:
        st.markdown(
            '<div class="upload-hint">📂 Upload your DEGIRO CSV to get started</div>',
            unsafe_allow_html=True
        )
        return

    # Ticker validi
    valid_tickers = tuple(sorted([
        str(t) for t in positions_df["ticker"].dropna().unique() if t
    ]))
    if not valid_tickers:
        st.warning("No valid tickers found. Re-upload CSV."); return

    # ---- PREZZI E FX ----
    with st.spinner("Loading market data..."):
        curr_px  = fetch_current_prices(valid_tickers)
        fx_rates = fetch_fx_rates()

    # ---- BUY PRICES & COMMISSIONS ----
    if "buy_prices"  not in st.session_state:
        st.session_state["buy_prices"]  = load_buy_prices()
    if "commissions" not in st.session_state:
        st.session_state["commissions"] = load_commissions()
    buy_prices  = st.session_state["buy_prices"]
    commissions = st.session_state["commissions"]

    if is_admin:
        with st.expander("⚙️ Edit Buy Prices & Transactions", expanded=False):
            st.caption("Buy prices used for P&L. Transaction count for commission calculation.")
            n = max(1, min(len(positions_df), 4))
            bp_cols = st.columns(n)
            for i, (_, pos) in enumerate(positions_df.iterrows()):
                isin    = str(_col(pos, "isin"))
                name    = str(_col(pos, "yf_name", "name", default=isin))[:20]
                cur     = ISIN_MAP.get(isin, {}).get("currency",
                          str(_col(pos, "currency", default="EUR")))
                rate    = 1 if cur == "EUR" else 3
                curr_bp = float(buy_prices.get(isin, 0.0))
                curr_tx = int(commissions.get(isin, 1))
                with bp_cols[i % n]:
                    new_bp = st.number_input(
                        f"{name} ({cur})", min_value=0.0,
                        value=curr_bp, step=0.01, format="%.4f",
                        key=f"bp_{isin}"
                    )
                    new_tx = st.number_input(
                        f"Transactions (€{rate}/tx)", min_value=1,
                        max_value=50, value=curr_tx, step=1,
                        key=f"tx_{isin}"
                    )
                    if new_bp != curr_bp:
                        buy_prices[isin] = new_bp
                        st.session_state["buy_prices"] = buy_prices
                        save_buy_prices(buy_prices)
                    if new_tx != curr_tx:
                        commissions[isin] = new_tx
                        st.session_state["commissions"] = commissions
                        save_commissions(commissions)

    # ---- CALCOLO PORTAFOGLIO ----
    try:
        pivot, total_value = calc_portfolio(
            positions_df, curr_px, fx_rates, buy_prices, commissions
        )
    except Exception as e:
        st.error(f"Portfolio calculation error: {e}")
        return

    total_cost        = pd.to_numeric(pivot.get("Cost (€)"),       errors="coerce").sum()
    total_commissions = pd.to_numeric(pivot.get("Commission (€)"), errors="coerce").sum()
    total_pl          = pd.to_numeric(pivot.get("P&L (€)"),        errors="coerce").sum()
    total_pl_pct      = total_pl / total_cost if total_cost > 0 else 0

    # Auto-save snapshot (silenzioso, mai crashare)
    _save_snapshot(total_value, total_pl, total_pl_pct)

    # ---- KPI ----
    section("Overview")
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Total Value", f"€{total_value:,.0f}", C["blue"],
                  "Valore corrente totale in EUR.")
    with k2: kpi("P&L (net commissions)",
                  f"€{total_pl:+,.0f} ({total_pl_pct:+.1%})",
                  C["green"] if total_pl >= 0 else C["red"],
                  "P&L non realizzata al netto delle commissioni.")
    with k3: kpi("Total Commissions", f"€{total_commissions:,.2f}", C["muted"],
                  "€1/tx EUR · €3/tx altre valute.")
    with k4: kpi("Monthly Budget", f"€{budget:,.0f}", C["purple"],
                  "Budget mensile per nuovi acquisti.")

    # ---- TABELLA POSIZIONI ----
    section("Positions")
    try:
        disp = pivot.drop(
            columns=["_val_orig","_pl_orig","Cost (€)","P&L (€)","Commission (€)"],
            errors="ignore"
        ).copy()
        disp["P&L (%)"]      = disp["P&L (%)"].apply(
            lambda x: f"{x:+.2%}" if pd.notna(x) else "—")
        disp["Weight"]       = disp["Weight"].apply(
            lambda x: f"{x:.1%}" if pd.notna(x) else "—")
        disp["Value (€) YF"] = disp["Value (€) YF"].apply(
            lambda x: f"€{x:,.2f}" if pd.notna(x) else "—")

        # Yield implicito per ETF accumulo
        yield_col = {}
        for ticker in pivot.index:
            isin_rows = positions_df[positions_df["ticker"] == ticker]
            isin_val  = str(isin_rows["isin"].values[0]) if not isin_rows.empty else ""
            is_acc    = ISIN_MAP.get(isin_val, {}).get("accumulation", False)
            if is_acc:
                y = fetch_implicit_yield(ticker)
                yield_col[ticker] = f"~{y:.2%}" if y else "—"
            else:
                yield_col[ticker] = "—"
        disp["Yield/Impl."] = pd.Series(yield_col)

        cols_show = [c for c in ["Name","Currency","Qty","Buy Price",
                                   "Current Price (YF)","Value (orig)","P&L (orig)",
                                   "P&L (%)","Value (€) YF","Weight","Yield/Impl."]
                     if c in disp.columns]
        render_table(disp[cols_show].fillna("—"))
    except Exception as e:
        st.warning(f"Table error: {e}")
        st.dataframe(pivot, use_container_width=True)

    # ---- ALLOCATION ----
    section("Allocation & Monthly Budget")
    col_pie, col_alloc = st.columns(2)

    with col_pie:
        vals = pd.to_numeric(pivot.get("Value (€) YF"), errors="coerce").fillna(0)
        fig_pie = go.Figure(go.Pie(
            labels=pivot.index.tolist(), values=vals.tolist(), hole=0.5,
            textinfo="label+percent", textfont=dict(color=C["text"], size=11),
            marker=dict(colors=CHART_COLORS, line=dict(color=C["bg"], width=2)),
            hovertemplate="<b>%{label}</b><br>€%{value:,.2f} · %{percent}<extra></extra>"
        ))
        fig_pie.add_annotation(
            text=f"€{total_value:,.0f}", x=0.5, y=0.5,
            font=dict(size=16, color=C["text"], family="Inter"), showarrow=False
        )
        apply_layout(fig_pie, "Portfolio Allocation", 360)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_alloc:
        alloc_rows = []
        for ticker, row in pivot.iterrows():
            w     = float(row["Weight"]) if isinstance(row["Weight"], float) else 0
            bud   = budget * w
            cp    = curr_px.get(ticker)
            cur   = str(row.get("Currency", "EUR"))
            fx    = fx_rates.get(cur, 1.0)
            p_eur = cp * fx if cp else None
            isin_rows = positions_df[positions_df["ticker"] == ticker]
            isin_val  = str(isin_rows["isin"].values[0]) if not isin_rows.empty else ""
            comm  = 1.0 if ISIN_MAP.get(isin_val,{}).get("currency","EUR") == "EUR" else 3.0
            alloc_rows.append({
                "Weight":      f"{w:.1%}",
                "Budget":      f"€{bud:.2f}",
                "Price (€)":   f"€{p_eur:.2f}" if p_eur else "—",
                "Units":       f"{bud/p_eur:.3f}" if p_eur else "—",
                "Commission":  f"€{comm:.0f}" if bud > 0 else "—",
            })
        alloc_df = pd.DataFrame(alloc_rows, index=pivot.index)
        alloc_df.loc["TOTAL"] = ["100%", f"€{budget:.2f}", "", "", ""]
        render_table(alloc_df)

    # P&L bar
    pl_vals = pd.to_numeric(pivot.get("P&L (€)"), errors="coerce")
    pl_cols = [C["green"] if (pd.notna(v) and v >= 0) else C["red"] for v in pl_vals]
    fig_pl  = go.Figure(go.Bar(
        x=pivot.index.tolist(), y=pl_vals.tolist(),
        marker_color=pl_cols, opacity=0.85,
        text=[f"€{v:+,.0f}" if pd.notna(v) else "" for v in pl_vals],
        textposition="outside", textfont=dict(color=C["text"], size=11),
        hovertemplate="<b>%{x}</b><br>P&L: €%{y:+,.2f}<extra></extra>"
    ))
    fig_pl.add_hline(y=0, line_color=C["muted"], line_width=1)
    apply_layout(fig_pl, f"Unrealised P&L  |  Total: €{total_pl:+,.0f}", 300)
    st.plotly_chart(fig_pl, use_container_width=True)

    # ---- TOP 3 WATCHLIST ----
    section("Top 3 per Category (Watchlist)")
    st.caption("Best 3 assets by composite score. Updates every hour.")
    with st.spinner("Computing scores..."):
        scores_by_cat = {}
        for cat, names in UNIVERSE.items():
            try:
                scores_by_cat[cat] = compute_scores(cat, tuple(names.items()))
            except:
                scores_by_cat[cat] = None
    render_top3_cards(scores_by_cat)

    # ---- HISTORY ----
    section("Portfolio History")
    snaps = _load_snapshots()
    if len(snaps) < 2:
        st.caption(
            f"📸 Snapshot saved automatically every time you open this page. "
            f"{len(snaps)}/2 so far — come back tomorrow to see the chart."
        )
    else:
        dates  = [s["date"]  for s in snaps]
        values = [s["value"] for s in snaps]
        pls    = [s["pl"]    for s in snaps]

        col_h1, col_h2 = st.columns(2)
        with col_h1:
            fig_v = go.Figure(go.Scatter(
                x=dates, y=values, fill="tozeroy",
                fillcolor="rgba(0,180,255,0.10)",
                line=dict(color=C["blue"], width=2),
                hovertemplate="%{x}: €%{y:,.2f}<extra></extra>"
            ))
            apply_layout(fig_v, "Portfolio Value Over Time (€)", 280)
            st.plotly_chart(fig_v, use_container_width=True)

        with col_h2:
            fig_pl2 = go.Figure(go.Scatter(
                x=dates, y=pls, fill="tozeroy",
                fillcolor="rgba(0,255,148,0.10)" if pls[-1] >= 0 else "rgba(255,59,59,0.10)",
                line=dict(color=C["green"] if pls[-1] >= 0 else C["red"], width=2),
                hovertemplate="%{x}: €%{y:+,.2f}<extra></extra>"
            ))
            fig_pl2.add_hline(y=0, line_color=C["muted"], line_width=1)
            apply_layout(fig_pl2, "Unrealised P&L Over Time (€)", 280)
            st.plotly_chart(fig_pl2, use_container_width=True)

        snap_df = pd.DataFrame({
            "Value":    [f"€{v:,.0f}" for v in values],
            "P&L":      [f"€{p:+,.0f}" for p in pls],
            "Δ vs prev":[f"{(values[i]-values[i-1])/values[i-1]:+.1%}"
                         if i > 0 and values[i-1] > 0 else "—"
                         for i in range(len(values))],
        }, index=dates)
        render_table(snap_df.iloc[::-1].head(12))

    # ---- RISK ----
    section("Risk Analysis")
    try:
        prices_ptf    = fetch_prices(valid_tickers, "3y")
        value_weights = {
            t: float(pivot.loc[t, "Value (€) YF"])
            for t in valid_tickers
            if t in pivot.index and pd.notna(pivot.loc[t, "Value (€) YF"])
        }
        port_ret = build_port_returns(prices_ptf, value_weights)
        if port_ret is not None and len(port_ret) > 20:
            render_risk_charts(port_ret, total_value)
            valid_t = [t for t in valid_tickers if t in prices_ptf.columns]
            if len(valid_t) > 1:
                corr = prices_ptf[valid_t].pct_change().dropna().corr()
                fig_c = go.Figure(go.Heatmap(
                    z=corr.values,
                    x=corr.columns.tolist(), y=corr.index.tolist(),
                    colorscale=[[0,C["red"]],[0.5,"#111"],[1,C["green"]]],
                    zmin=-1, zmax=1,
                    text=[[f"{v:.2f}" for v in row] for row in corr.values],
                    texttemplate="%{text}",
                    textfont=dict(color=C["text"], size=11),
                    hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>"
                ))
                apply_layout(fig_c, "Correlation Matrix", 340)
                st.plotly_chart(fig_c, use_container_width=True)
    except Exception as e:
        st.warning(f"Risk analysis unavailable: {e}")

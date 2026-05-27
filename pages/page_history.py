"""
pages/page_history.py — Tracking storico portafoglio + Watchlist.
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, UNIVERSE, SNAPSHOTS_FILE
from data import fetch_current_prices, fetch_fx_rates, fetch_prices
from portfolio import calc_portfolio, load_buy_prices, load_commissions, load_cached_portfolio
from scoring import compute_scores
from ui import kpi, section, apply_layout, render_score_chart

WATCHLIST_FILE = Path("watchlist.json")


# ------------------------------------------------------------------ #
#  SNAPSHOT HELPERS
# ------------------------------------------------------------------ #

def load_snapshots() -> list:
    if SNAPSHOTS_FILE.exists():
        with open(SNAPSHOTS_FILE) as f:
            return json.load(f)
    return []

def save_snapshot(total_value: float, pl_eur: float, positions: dict) -> None:
    snapshots = load_snapshots()
    today = datetime.now().strftime("%Y-%m-%d")
    # Aggiorna snapshot del giorno se già esiste
    snapshots = [s for s in snapshots if s["date"] != today]
    snapshots.append({
        "date":        today,
        "total_value": round(total_value, 2),
        "pl_eur":      round(pl_eur, 2),
        "positions":   positions,
    })
    snapshots.sort(key=lambda x: x["date"])
    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump(snapshots, f, indent=2)

# ------------------------------------------------------------------ #
#  WATCHLIST HELPERS
# ------------------------------------------------------------------ #

def load_watchlist() -> dict:
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return {}

def save_watchlist(data: dict) -> None:
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------ #
#  RENDER
# ------------------------------------------------------------------ #

def render(is_admin: bool) -> None:
    tab_history, tab_watchlist = st.tabs(["📈 Portfolio History", "👁 Watchlist"])

    # ================================================================
    #  TAB 1 — PORTFOLIO HISTORY
    # ================================================================
    with tab_history:
        st.title("📈 Portfolio History")
        st.caption("Each time you upload a DEGIRO CSV, a snapshot is saved automatically. "
                   "Over time you build a real history of your portfolio growth.")

        # Auto-save snapshot se c'è un portafoglio in sessione
        positions_df = st.session_state.get("positions_df")
        if positions_df is not None and not positions_df.empty:
            try:
                curr_px     = fetch_current_prices(tuple(sorted(positions_df["ticker"].dropna().unique())))
                fx_rates    = fetch_fx_rates()
                buy_prices  = load_buy_prices()
                commissions = load_commissions()
                pivot, total_value = calc_portfolio(positions_df, curr_px, fx_rates,
                                                     buy_prices, commissions)
                total_pl = pd.to_numeric(pivot["P&L (€)"], errors="coerce").sum()

                # Salva snapshot
                positions_summary = {
                    str(idx): {
                        "value_eur": float(row["Value (€) YF"]) if pd.notna(row.get("Value (€) YF")) else 0,
                        "pl_eur":    float(row["P&L (€)"])     if pd.notna(row.get("P&L (€)"))     else 0,
                        "weight":    float(row["Weight"])       if isinstance(row.get("Weight"), float) else 0,
                    }
                    for idx, row in pivot.iterrows()
                }
                save_snapshot(total_value, total_pl, positions_summary)
            except Exception as e:
                st.warning(f"Could not save snapshot: {e}")

        snapshots = load_snapshots()

        if len(snapshots) < 2:
            st.markdown('<div class="upload-hint">'
                        '📂 Upload your DEGIRO CSV at least twice (on different days) '
                        'to start building your history.'
                        '</div>', unsafe_allow_html=True)
            if snapshots:
                st.caption(f"Current snapshots: {len(snapshots)} — need at least 2.")
            return

        # Costruisci serie storica
        dates  = [s["date"] for s in snapshots]
        values = [s["total_value"] for s in snapshots]
        pls    = [s["pl_eur"] for s in snapshots]

        # KPI
        first_val = values[0]
        last_val  = values[-1]
        total_growth     = (last_val - first_val) / first_val if first_val > 0 else 0
        latest_pl        = pls[-1]
        n_months         = max(1, len(snapshots))

        section("Portfolio Growth")
        k1,k2,k3,k4 = st.columns(4)
        with k1: kpi("Current Value",    f"€{last_val:,.0f}",         C["blue"],
                      "Valore corrente del portafoglio all'ultimo snapshot.")
        with k2: kpi("Total Growth",     f"{total_growth:+.2%}",
                      C["green"] if total_growth >= 0 else C["red"],
                      f"Crescita dal primo snapshot (€{first_val:,.0f}) ad oggi.")
        with k3: kpi("Current P&L",      f"€{latest_pl:+,.0f}",
                      C["green"] if latest_pl >= 0 else C["red"],
                      "P&L non realizzato all'ultimo aggiornamento.")
        with k4: kpi("Snapshots",        str(len(snapshots)),          C["teal"],
                      "Numero di snapshot salvati. Uno per ogni giorno in cui hai caricato il CSV.")

        # Grafico valore nel tempo
        fig_val = go.Figure()
        fig_val.add_trace(go.Scatter(
            x=dates, y=values, name="Portfolio Value (€)",
            fill="tozeroy", fillcolor="rgba(0,180,255,0.12)",
            line=dict(color=C["blue"], width=2),
            hovertemplate="%{x}: €%{y:,.2f}<extra></extra>"
        ))
        apply_layout(fig_val, "Portfolio Value Over Time (€)", 380)
        st.plotly_chart(fig_val, use_container_width=True)

        # Grafico P&L nel tempo
        pl_colors_line = C["green"] if pls[-1] >= 0 else C["red"]
        fig_pl = go.Figure()
        fig_pl.add_trace(go.Scatter(
            x=dates, y=pls, name="P&L (€)",
            fill="tozeroy",
            fillcolor="rgba(0,255,148,0.12)" if pls[-1] >= 0 else "rgba(255,59,59,0.12)",
            line=dict(color=pl_colors_line, width=2),
            hovertemplate="%{x}: €%{y:+,.2f}<extra></extra>"
        ))
        fig_pl.add_hline(y=0, line_color=C["muted"], line_width=1)
        apply_layout(fig_pl, "Unrealised P&L Over Time (€)", 300)
        st.plotly_chart(fig_pl, use_container_width=True)

        # Tabella snapshot
        section("Snapshot History")
        snap_df = pd.DataFrame({
            "Date":          dates,
            "Total Value":   [f"€{v:,.2f}" for v in values],
            "P&L (€)":       [f"€{p:+,.2f}" for p in pls],
            "Change vs prev":[f"{(values[i]-values[i-1])/values[i-1]:+.2%}"
                              if i > 0 and values[i-1] > 0 else "—"
                              for i in range(len(values))],
        }).set_index("Date")
        st.dataframe(snap_df[::-1], use_container_width=True)

        if is_admin:
            if st.button("🗑 Clear all snapshots", key="clear_snap"):
                with open(SNAPSHOTS_FILE, "w") as f:
                    json.dump([], f)
                st.success("Snapshots cleared.")
                st.rerun()

    # ================================================================
    #  TAB 2 — WATCHLIST
    # ================================================================
    with tab_watchlist:
        st.title("👁 Watchlist")
        st.caption("Track assets you're considering but haven't bought yet. "
                   "See scores and metrics without adding to your real portfolio.")

        if "watchlist" not in st.session_state:
            st.session_state["watchlist"] = load_watchlist()
        watchlist = st.session_state["watchlist"]

        # Aggiungi asset
        if is_admin:
            section("Add to Watchlist")
            all_tickers = {t: f"{t} — {n} ({cat})"
                           for cat, items in UNIVERSE.items()
                           for t, n in items.items()}

            c1, c2, c3 = st.columns([2,1,1])
            with c1:
                add_t = st.selectbox("Select asset", [""] + sorted(all_tickers.keys()),
                                      format_func=lambda x: all_tickers.get(x,x) if x else "— Select —",
                                      key="wl_add_t")
            with c2:
                add_note = st.text_input("Note (optional)", key="wl_note",
                                          placeholder="e.g. waiting for dip")
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ Add", type="primary", key="wl_btn") and add_t:
                    watchlist[add_t] = {
                        "ticker":   add_t,
                        "name":     all_tickers.get(add_t, add_t),
                        "note":     add_note,
                        "added_at": datetime.now().strftime("%Y-%m-%d"),
                    }
                    st.session_state["watchlist"] = watchlist
                    save_watchlist(watchlist)
                    st.rerun()

            # Custom ticker
            with st.expander("Add custom ticker"):
                cc1, cc2 = st.columns([2,1])
                with cc1: ct = st.text_input("Yahoo ticker", key="wl_ct").upper().strip()
                with cc2: cn = st.text_input("Note", key="wl_cn")
                if st.button("➕ Add custom", key="wl_ct_btn") and ct:
                    watchlist[ct] = {"ticker":ct,"name":ct,"note":cn,
                                     "added_at":datetime.now().strftime("%Y-%m-%d")}
                    st.session_state["watchlist"] = watchlist
                    save_watchlist(watchlist)
                    st.rerun()

        if not watchlist:
            st.markdown('<div class="upload-hint">👁 No assets on watchlist yet. Add some above.</div>',
                        unsafe_allow_html=True)
            return

        # Mostra watchlist con prezzi correnti
        section(f"Watching {len(watchlist)} assets")
        wl_tickers = tuple(sorted(watchlist.keys()))

        with st.spinner("Loading watchlist prices..."):
            curr_px  = fetch_current_prices(wl_tickers)
            fx_rates = fetch_fx_rates()

        wl_rows = []
        for ticker, info in watchlist.items():
            px  = curr_px.get(ticker)
            wl_rows.append({
                "Ticker":    ticker,
                "Name":      info.get("name",""),
                "Price":     f"{px:.2f}" if px else "N/A",
                "Note":      info.get("note",""),
                "Added":     info.get("added_at",""),
            })

        wl_df = pd.DataFrame(wl_rows).set_index("Ticker")
        st.dataframe(wl_df, use_container_width=True)

        # Remove
        if is_admin:
            remove_t = st.selectbox("Remove from watchlist", [""] + list(watchlist.keys()),
                                     key="wl_remove")
            if st.button("🗑 Remove", key="wl_remove_btn") and remove_t:
                del watchlist[remove_t]
                st.session_state["watchlist"] = watchlist
                save_watchlist(watchlist)
                st.rerun()

        # Score per asset in watchlist
        section("Scores for Watchlist Assets")
        st.caption("Scores compared within their category universe.")

        cat_colors = {
            "UCITS Accumulation": C["blue"],   "ETF Accumulation": C["green"],
            "Dividend Stocks":    C["orange"],  "Growth Stocks":    C["purple"],
            "Macro Assets":       C["teal"],
        }

        # Trova categoria per ogni ticker in watchlist
        ticker_to_cat = {}
        for cat, items in UNIVERSE.items():
            for t in items:
                if t in watchlist:
                    ticker_to_cat[t] = cat

        for cat in set(ticker_to_cat.values()):
            cat_tickers = [t for t,c in ticker_to_cat.items() if c == cat]
            st.markdown(f"**{cat}**")
            with st.spinner(f"Loading {cat} scores..."):
                scores = compute_scores(cat, UNIVERSE[cat])
            if not scores.empty:
                # Evidenzia i ticker in watchlist
                wl_scores = scores[scores.index.isin(cat_tickers)]
                if not wl_scores.empty:
                    render_score_chart(scores, f"Score — {cat} (watchlist highlighted)",
                                       cat_colors[cat])
                    section(f"Watchlist positions in {cat}")
                    fmt = wl_scores.copy()
                    for col in fmt.columns:
                        if col == "Name": continue
                        elif col == "Score":
                            fmt[col] = fmt[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
                        elif any(k in col for k in ["Return","Growth","Yield","Margin","ROE","Vol","Momentum"]):
                            fmt[col] = fmt[col].map(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
                        else:
                            fmt[col] = fmt[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
                    st.dataframe(fmt, use_container_width=True)


import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from config import C, CHART_COLORS, WATCHLIST_FILE
from data import fetch_macro, fetch_news
from portfolio import load_cached_portfolio
from ui import kpi, section, apply_layout, render_news


def render() -> None:
    st.title("🌍 Macro & News")

    tab_macro, tab_news = st.tabs(["📊 Macroeconomic Context", "📰 News Feed"])

    # ================================================================
    #  TAB 1 — MACRO
    # ================================================================
    with tab_macro:
        st.caption("Data: FRED (Federal Reserve) + ECB. Cache: 12 hours.")
        macro = fetch_macro()

        if macro.empty:
            st.info("Macro data unavailable."); return

        latest = macro.ffill().iloc[-1]

        # Row 1: Rates
        section("Interest Rates & Monetary Policy")
        k1,k2,k3,k4 = st.columns(4)
        with k1: kpi("Fed Funds Rate",
                      f"{latest.get('Fed Funds Rate', float('nan')):.2f}%", C["blue"],
                      "Tasso di riferimento della Federal Reserve USA. "
                      "Alto = credito costoso, pressione su valutazioni azionarie.")
        with k2:
            yc = latest.get("Yield Curve 10-2", float("nan"))
            kpi("Yield Curve 10Y-2Y",
                f"{yc:.2f}%  {'⚠️ Inverted' if yc<0 else '✅ Normal'}",
                C["red"] if yc<0 else C["green"],
                "Spread tra Treasury 10Y e 2Y. Negativo = curva invertita, "
                "storicamente segnale di recessione nei 6-18 mesi successivi.")
        with k3:
            ecb = latest.get("ECB Rate", float("nan"))
            kpi("ECB Rate",
                f"{ecb:.2f}%" if ecb == ecb else "N/A", C["teal"],
                "Tasso di riferimento della Banca Centrale Europea. "
                "Influenza direttamente il costo del credito nell'Eurozona.")
        with k4: kpi("10Y Treasury",
                      f"{latest.get('10Y Treasury', float('nan')):.2f}%", C["purple"],
                      "Rendimento del titolo di stato USA 10 anni. "
                      "Benchmark globale risk-free. Alto = pressione sulle valutazioni azionarie.")

        # Row 2: Inflation & Economy
        section("Inflation & Economy")
        k5,k6,k7,k8 = st.columns(4)
        with k5: kpi("US CPI",
                      f"{latest.get('US CPI', float('nan')):.1f}", C["orange"],
                      "Indice prezzi al consumo USA. Crescita accelerata "
                      "spinge la Fed ad alzare i tassi.")
        with k6: kpi("US Unemployment",
                      f"{latest.get('US Unemployment', float('nan')):.1f}%", C["yellow"],
                      "Tasso di disoccupazione USA. Bassa disoccupazione = "
                      "economia forte ma rischio inflazione salariale.")
        with k7: kpi("EUR/USD",
                      f"{latest.get('EUR/USD', float('nan')):.4f}", C["pink"],
                      "Tasso cambio Euro/Dollaro. EUR/USD alto = euro forte, "
                      "riduce il valore EUR degli asset denominati in USD.")
        with k8: kpi("VIX",
                      f"{latest.get('VIX', float('nan')):.1f}", C["red"],
                      "Fear Index: volatilità implicita del mercato USA. "
                      "<20 calmo · 20-30 incerto · >30 panico.")

        st.markdown("---")

        # Grafici selezionabili — due per riga
        all_series = [c for c in macro.columns if c in macro.columns]
        selected = st.multiselect(
            "Select indicators to display",
            options=all_series,
            default=all_series[:6] if len(all_series)>=6 else all_series
        )

        if selected:
            for i in range(0, len(selected), 2):
                row_cols = st.columns(2)
                for j, col_name in enumerate(selected[i:i+2]):
                    with row_cols[j]:
                        s      = macro[col_name].dropna().iloc[-15*12:]
                        color  = CHART_COLORS[(i+j) % len(CHART_COLORS)]
                        r,g,b  = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
                        is_neg = col_name in ["Yield Curve 10-2"]
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=s.index, y=s.values, fill="tozeroy",
                            fillcolor=f"rgba({r},{g},{b},0.10)",
                            line=dict(color=color, width=2),
                            hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"
                        ))
                        if is_neg:
                            fig.add_hrect(y0=-20, y1=0, fillcolor="rgba(255,59,59,0.05)",
                                          line_width=0, annotation_text="Inverted",
                                          annotation_font_color=C["red"],
                                          annotation_font_size=10)
                        last = s.iloc[-1]
                        fig.add_annotation(
                            text=f"  {last:.2f}", x=s.index[-1], y=last,
                            font=dict(size=12,color=color), showarrow=False
                        )
                        apply_layout(fig, col_name, 260)
                        st.plotly_chart(fig, use_container_width=True)

    # ================================================================
    #  TAB 2 — NEWS
    # ================================================================
    with tab_news:
        st.caption(
            "News aggregated from yfinance for your portfolio and watchlist positions. "
            "Trusted sources (Reuters, FT, Bloomberg, CNBC) shown first. Last 7 days only."
        )

        # Raccogli ticker da portafoglio + watchlist
        portfolio_tickers = []
        # Load positions — robusto, mai crashare
    positions_df = st.session_state.get("positions_df")
    if positions_df is None:
        import json
        cache_file = Path("last_portfolio.json")
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    raw = json.load(f)
                if isinstance(raw, list) and raw:
                    df_tmp = pd.DataFrame(raw)
                    if "ticker" in df_tmp.columns:
                        positions_df = df_tmp
                        st.session_state["positions_df"] = positions_df
            except:
                pass
        if positions_df is not None and not positions_df.empty:
            portfolio_tickers = [t for t in positions_df["ticker"].dropna().unique() if t]

        watchlist_tickers = []
        if WATCHLIST_FILE.exists():
            with open(WATCHLIST_FILE) as f:
                wl = json.load(f)
            watchlist_tickers = list(wl.keys())

        all_news_tickers = list(dict.fromkeys(portfolio_tickers + watchlist_tickers))

        if not all_news_tickers:
            st.markdown('<div class="upload-hint">📂 Upload DEGIRO CSV and add to watchlist '
                        'to see relevant news.</div>', unsafe_allow_html=True)
            return

        # Filtri
        col_f1, col_f2 = st.columns([2,1])
        with col_f1:
            selected_tickers = st.multiselect(
                "Filter by ticker",
                options=all_news_tickers,
                default=all_news_tickers,
                key="news_filter"
            )
        with col_f2:
            trusted_only = st.checkbox("Trusted sources only", value=False)

        if not selected_tickers:
            st.info("Select at least one ticker."); return

        with st.spinner("Fetching latest news..."):
            news = fetch_news(tuple(selected_tickers), max_per_ticker=8)

        if trusted_only:
            news = [n for n in news if n["trusted"]]

        # Raggruppa per ticker
        col_ptf, col_wl = st.columns(2)

        ptf_news = [n for n in news if n["ticker"] in portfolio_tickers]
        wl_news  = [n for n in news if n["ticker"] in watchlist_tickers
                    and n["ticker"] not in portfolio_tickers]

        with col_ptf:
            section(f"Portfolio ({len(portfolio_tickers)} assets)")
            render_news(ptf_news, max_items=15)

        with col_wl:
            section(f"Watchlist ({len(watchlist_tickers)} assets)")
            if watchlist_tickers:
                render_news(wl_news, max_items=15)
            else:
                st.caption("Add assets to watchlist in My Portfolio → Top 3 section.")

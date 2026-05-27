"""
portfolio.py — Parsing CSV DEGIRO, calcolo metriche, commissioni, buy prices.
"""
import json
import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
from config import ISIN_MAP, PORTFOLIO_CACHE, BUY_PRICES_FILE, COMMISSIONS_FILE


# ------------------------------------------------------------------ #
#  PERSISTENZA
# ------------------------------------------------------------------ #

def load_buy_prices() -> dict:
    if BUY_PRICES_FILE.exists():
        with open(BUY_PRICES_FILE) as f:
            return json.load(f)
    return {}

def save_buy_prices(data: dict) -> None:
    with open(BUY_PRICES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_commissions() -> dict:
    if COMMISSIONS_FILE.exists():
        with open(COMMISSIONS_FILE) as f:
            return json.load(f)
    return {}

def save_commissions(data: dict) -> None:
    with open(COMMISSIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_cached_portfolio() -> pd.DataFrame | None:
    if PORTFOLIO_CACHE.exists():
        try:
            return pd.read_json(PORTFOLIO_CACHE, orient="records")
        except:
            return None
    return None

def save_cached_portfolio(df: pd.DataFrame) -> None:
    df.to_json(PORTFOLIO_CACHE, orient="records")

def commission_rate(currency: str) -> float:
    """€1 per transazione EUR, €3 per altre valute."""
    return 1.0 if currency == "EUR" else 3.0

def calc_total_commission(isin: str, currency: str, n_transactions: int) -> float:
    return commission_rate(currency) * n_transactions


# ------------------------------------------------------------------ #
#  CSV PARSER
# ------------------------------------------------------------------ #

def parse_degiro_csv(uploaded_file) -> tuple:
    """
    Parsa CSV portafoglio DEGIRO.
    Returns (positions_df, unmapped_isins)
    """
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        col_map = {
            "Prodotto": "name",    "Product": "name",
            "Codice":   "isin",    "Symbol/ISIN": "isin",
            "Quantità": "qty",     "Quantity": "qty",
            "Ultimo":   "degiro_price", "Last": "degiro_price",
            "Valore in EUR": "degiro_value_eur", "Value in EUR": "degiro_value_eur",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Gestisci colonna valuta unnamed
        unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
        if unnamed:
            df = df.rename(columns={unnamed[0]: "degiro_currency_raw"})
        for c in df.columns:
            if c in ["Valore", "Value", "Local value"] and c not in col_map:
                df = df.rename(columns={c: "degiro_value_local"})
                break

        # Pulizia numerica
        if "qty" in df.columns:
            df["qty"] = pd.to_numeric(df["qty"], errors="coerce")

        def clean_num(s):
            return pd.to_numeric(
                s.astype(str).str.replace('"','',regex=False)
                              .str.replace('€','',regex=False)
                              .str.strip()
                              .str.replace(',','.',regex=False),
                errors="coerce")

        for col in ["degiro_price", "degiro_value_eur", "degiro_value_local"]:
            if col in df.columns:
                df[col] = clean_num(df[col])

        if "degiro_currency_raw" in df.columns:
            df["degiro_currency"] = df["degiro_currency_raw"].astype(str).str.strip()
        else:
            df["degiro_currency"] = "EUR"

        # Filtra cash e righe senza ISIN
        df = df.dropna(subset=["isin"])
        df = df[~df["isin"].astype(str).str.upper().str.contains("CASH|FUND|FTX", na=False)]
        df = df[df["qty"].notna() & (df["qty"] > 0)].reset_index(drop=True)

        # Mappa ISIN → ticker
        unmapped, tickers, currencies, yf_names = [], [], [], []
        for _, row in df.iterrows():
            isin = str(row["isin"]).strip()
            if isin in ISIN_MAP:
                tickers.append(ISIN_MAP[isin]["ticker"])
                currencies.append(ISIN_MAP[isin]["currency"])
                yf_names.append(ISIN_MAP[isin]["name"])
            else:
                tickers.append(None)
                currencies.append(str(row.get("degiro_currency","EUR")))
                yf_names.append(str(row.get("name","")))
                unmapped.append(isin)

        df["ticker"]   = tickers
        df["currency"] = currencies
        df["yf_name"]  = yf_names
        return df, unmapped

    except Exception as e:
        st.error(f"CSV parse error: {e}")
        import traceback; st.code(traceback.format_exc())
        return pd.DataFrame(), []


# ------------------------------------------------------------------ #
#  CALCOLO METRICHE
# ------------------------------------------------------------------ #

def calc_portfolio(positions_df: pd.DataFrame, current_prices: dict,
                   fx_rates: dict, buy_prices: dict = None,
                   commissions: dict = None) -> tuple:
    """
    Calcola pivot table portafoglio.
    P&L in valuta originale, valore totale in EUR.
    """
    if buy_prices   is None: buy_prices   = {}
    if commissions  is None: commissions  = {}

    rows = []
    total_value = 0.0

    for _, pos in positions_df.iterrows():
        ticker      = pos.get("ticker")
        isin        = str(pos.get("isin", ""))
        qty         = float(pos["qty"])
        degiro_px   = float(pos["degiro_price"]) if pd.notna(pos.get("degiro_price")) else 0
        currency    = pos.get("currency", "EUR")
        fx          = fx_rates.get(currency, 1.0)
        curr_px     = current_prices.get(ticker) if ticker else None
        deg_val_eur = pos.get("degiro_value_eur")
        deg_currency= pos.get("degiro_currency", currency)

        # Buy price: manuale se disponibile, altrimenti DEGIRO
        has_manual  = isin in buy_prices and buy_prices[isin] > 0
        buy_px      = float(buy_prices[isin]) if has_manual else degiro_px
        price_source= "Manual" if has_manual else "DEGIRO (fallback)"

        # Commissioni basate su currency mappata (EUR=1€, altre=3€)
        n_tx           = int(commissions.get(isin, 1))
        commission_eur = calc_total_commission(isin, currency, n_tx)
        commission_orig= commission_eur / fx if fx > 0 else commission_eur

        # P&L in valuta originale, netto commissioni
        cost_orig   = qty * buy_px
        val_orig    = qty * curr_px if curr_px else None
        pl_orig_pre = (val_orig - cost_orig) if val_orig is not None else None
        pl_orig     = (pl_orig_pre - commission_orig) if pl_orig_pre is not None else None
        pl_pct      = (pl_orig / cost_orig) if (pl_orig is not None and cost_orig > 0) else None

        # EUR
        val_eur  = val_orig * fx if val_orig is not None else cost_orig * fx
        pl_eur   = pl_orig  * fx if pl_orig  is not None else None
        cost_eur = cost_orig * fx

        total_value += val_eur

        rows.append({
            "Ticker":             ticker or isin or "N/A",
            "Name":               str(pos.get("yf_name", pos.get("name",""))),
            "ISIN":               isin,
            "Currency":           deg_currency,
            "Qty":                qty,
            "Buy Price":          f"{buy_px:.2f} {deg_currency}",
            "Price Source":       price_source,
            "DEGIRO Price":       f"{degiro_px:.2f} {deg_currency}" if degiro_px else "N/A",
            "Current Price (YF)": f"{curr_px:.2f} {currency}" if curr_px else "N/A",
            "Value (orig)":       f"{val_orig:,.2f} {currency}" if val_orig else "N/A",
            "P&L (orig)":         f"{pl_orig:+,.2f} {currency}" if pl_orig is not None else "N/A",
            "P&L (%)":            pl_pct,
            "Commission (€)":     commission_eur,
            "Value (€) YF":       round(val_eur, 2),
            "Value (€) DEGIRO":   round(float(deg_val_eur), 2) if pd.notna(deg_val_eur) else None,
            "P&L (€)":            round(pl_eur, 2) if pl_eur is not None else None,
            "Cost (€)":           round(cost_eur, 2),
            "_val_orig":          val_orig,
            "_pl_orig":           pl_orig,
        })

    df = pd.DataFrame(rows).set_index("Ticker")
    df["Weight"] = df["Value (€) YF"] / total_value if total_value > 0 else 0
    return df, total_value

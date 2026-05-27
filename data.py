"""
data.py — Fetch dati con cache ottimizzata.
Fonti: yfinance, FRED, ECB, RSS news feeds.
"""
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import yfinance as yf
import requests

from config import FRED_SERIES, TRUSTED_SOURCES


# ------------------------------------------------------------------ #
#  PREZZI
# ------------------------------------------------------------------ #

@st.cache_data(ttl=900)  # 15 min
def fetch_prices(tickers: tuple, period: str = "3y") -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    data = yf.download(list(tickers), period=period,
                       auto_adjust=True, progress=False, threads=True)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"].dropna(how="all")
    return data[["Close"]].rename(columns={"Close": tickers[0]}).dropna(how="all")


@st.cache_data(ttl=900)
def fetch_current_prices(tickers: tuple) -> dict:
    if not tickers:
        return {}
    result = {}
    try:
        data = yf.download(list(tickers), period="5d",
                           auto_adjust=True, progress=False)
        if not data.empty:
            closes = data["Close"].ffill().iloc[-1] if isinstance(data.columns, pd.MultiIndex) \
                     else pd.Series({tickers[0]: float(data["Close"].ffill().iloc[-1])})
            for t in tickers:
                if t in closes and not pd.isna(closes[t]):
                    result[t] = float(closes[t])
    except Exception as e:
        st.warning(f"Price error: {e}")
    return result


@st.cache_data(ttl=3600)
def fetch_fx_rates() -> dict:
    rates = {"EUR": 1.0}
    for cur, pair in {"USD": "EURUSD=X", "CHF": "EURCHF=X", "GBP": "EURGBP=X"}.items():
        try:
            d = yf.download(pair, period="2d", progress=False, auto_adjust=True)
            if not d.empty:
                rates[cur] = 1 / float(d["Close"].iloc[-1])
        except:
            pass
    return rates


# ------------------------------------------------------------------ #
#  FONDAMENTALI + DIVIDENDI + YIELD IMPLICITO
# ------------------------------------------------------------------ #

@st.cache_data(ttl=3600)
def fetch_fundamentals(tickers: tuple) -> pd.DataFrame:
    rows = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            rows[ticker] = {
                "Name":              info.get("longName", ticker),
                "Dividend Yield":    info.get("dividendYield"),
                "Div Yield (TTM)":   info.get("trailingAnnualDividendYield"),
                "Payout Ratio":      info.get("payoutRatio"),
                "ROE":               info.get("returnOnEquity"),
                "Revenue Growth":    info.get("revenueGrowth"),
                "EPS Growth":        info.get("earningsGrowth"),
                "Profit Margin":     info.get("profitMargins"),
                "Debt/Equity":       info.get("debtToEquity"),
                "Forward P/E":       info.get("forwardPE"),
                "Trailing P/E":      info.get("trailingPE"),
                "EV/EBITDA":         info.get("enterpriseToEbitda"),
                "FCF":               info.get("freeCashflow"),
                "Market Cap":        info.get("marketCap"),
                "Beta":              info.get("beta"),
                "Analyst Target":    info.get("targetMeanPrice"),
                "52W High":          info.get("fiftyTwoWeekHigh"),
                "52W Low":           info.get("fiftyTwoWeekLow"),
                "Expense Ratio":     info.get("annualReportExpenseRatio"),
                "Total Assets":      info.get("totalAssets"),
                "YTD Return":        info.get("ytdReturn"),
                "3Y Return":         info.get("threeYearAverageReturn"),
                "5Y Return":         info.get("fiveYearAverageReturn"),
            }
            time.sleep(0.25)
        except:
            rows[ticker] = {"Name": ticker}
    df = pd.DataFrame(rows).T
    df.index.name = "Ticker"
    for col in df.columns:
        if col != "Name":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=86400)
def fetch_dividends(tickers: tuple) -> dict:
    result = {}
    for t in tickers:
        try:
            result[t] = yf.Ticker(t).dividends
            time.sleep(0.2)
        except:
            result[t] = pd.Series(dtype=float)
    return result


@st.cache_data(ttl=3600)
def fetch_implicit_yield(ticker: str) -> float | None:
    """
    Per ETF ad accumulo: yield implicito del portafoglio sottostante.
    Usa yfinance info 'yield' o calcola da dividends se disponibile.
    Per UCITS europei fallback su trailingAnnualDividendYield della versione distribuzione.
    """
    try:
        info = yf.Ticker(ticker).info
        # Prova yield diretto
        y = info.get("yield") or info.get("trailingAnnualDividendYield")
        if y and y > 0:
            return float(y)
        # Per VWCE → prova VWRL (versione dist stesso indice)
        dist_map = {
            "VWCE.DE": "VWRL.AS",
            "IWDA.AS": "IWDA.L",
            "CSPX.L":  "CSPX.L",
            "SPPW.DE": "SWRD.L",
        }
        if ticker in dist_map:
            info2 = yf.Ticker(dist_map[ticker]).info
            y2 = info2.get("trailingAnnualDividendYield") or info2.get("yield")
            if y2 and y2 > 0:
                return float(y2)
    except:
        pass
    return None


# ------------------------------------------------------------------ #
#  MACRO — FRED + ECB
# ------------------------------------------------------------------ #

@st.cache_data(ttl=43200)  # 12 ore
def fetch_macro() -> pd.DataFrame:
    frames = {}
    for name, sid in FRED_SERIES.items():
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            df  = pd.read_csv(url, index_col=0, parse_dates=True, na_values=".")
            df.columns = [name]
            frames[name] = df[name]
            time.sleep(0.1)
        except:
            pass

    # ECB rate (gratis, no key)
    try:
        ecb_url = ("https://data-api.ecb.europa.eu/service/data/FM/"
                   "B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata")
        ecb_df = pd.read_csv(ecb_url)
        if "TIME_PERIOD" in ecb_df.columns and "OBS_VALUE" in ecb_df.columns:
            ecb_s = pd.Series(
                ecb_df["OBS_VALUE"].values,
                index=pd.to_datetime(ecb_df["TIME_PERIOD"]),
                name="ECB Rate"
            )
            frames["ECB Rate"] = ecb_s
    except:
        pass

    return pd.DataFrame(frames) if frames else pd.DataFrame()


# ------------------------------------------------------------------ #
#  NEWS — RSS + yfinance
# ------------------------------------------------------------------ #

def _is_trusted(url: str) -> tuple[bool, str]:
    """Verifica se un URL proviene da una fonte trusted. Ritorna (is_trusted, source_name)."""
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        for key, name in TRUSTED_SOURCES.items():
            if key in domain:
                return True, name
    except:
        pass
    return False, ""


def _clean_title(title: str) -> str:
    title = re.sub(r'<[^>]+>', '', title)
    return title.strip()


@st.cache_data(ttl=1800)  # 30 min
def fetch_news(tickers: tuple, max_per_ticker: int = 5) -> list:
    """
    Recupera news per una lista di ticker.
    Prioritizza fonti trusted. Filtra ultime 7 giorni.
    Returns list of dicts: {ticker, title, url, source, trusted, published, age_days}
    """
    news_items = []
    cutoff     = datetime.now() - timedelta(days=7)

    for ticker in tickers:
        try:
            raw_news = yf.Ticker(ticker).news or []
            for item in raw_news[:max_per_ticker * 2]:  # fetch di più, poi filtra
                title = _clean_title(item.get("title", ""))
                url   = item.get("link") or item.get("url") or ""
                ts    = item.get("providerPublishTime", 0)

                if not title or not url:
                    continue

                pub_dt   = datetime.fromtimestamp(ts) if ts else datetime.now()
                age_days = (datetime.now() - pub_dt).days

                if pub_dt < cutoff:
                    continue

                trusted, source_name = _is_trusted(url)
                if not source_name:
                    source_name = item.get("publisher", "Unknown")

                news_items.append({
                    "ticker":    ticker,
                    "title":     title,
                    "url":       url,
                    "source":    source_name,
                    "trusted":   trusted,
                    "published": pub_dt.strftime("%d %b %Y"),
                    "age_days":  age_days,
                })

            time.sleep(0.2)
        except:
            pass

    # Sort: trusted first, then by recency
    news_items.sort(key=lambda x: (not x["trusted"], x["age_days"]))

    # Deduplica per titolo simile
    seen_titles = set()
    deduped = []
    for item in news_items:
        key = item["title"][:60].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(item)

    return deduped

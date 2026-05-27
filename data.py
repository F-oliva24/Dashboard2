"""
data.py — Download e cache dati da yfinance e FRED.
Tutte le funzioni sono cached con st.cache_data.
"""
import time
import pandas as pd
import streamlit as st
import yfinance as yf
from config import FRED_SERIES


@st.cache_data(ttl=3600)
def fetch_prices(tickers: tuple, period: str = "3y") -> pd.DataFrame:
    data = yf.download(list(tickers), period=period,
                       auto_adjust=True, progress=False, threads=True)
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"].dropna(how="all")
    return data[["Close"]].rename(columns={"Close": tickers[0]}).dropna(how="all")


@st.cache_data(ttl=3600)
def fetch_current_prices(tickers: tuple) -> dict:
    result = {}
    try:
        data = yf.download(list(tickers), period="5d",
                           auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"].ffill().iloc[-1]
        else:
            closes = pd.Series({tickers[0]: float(data["Close"].ffill().iloc[-1])})
        for t in tickers:
            if t in closes and not pd.isna(closes[t]):
                result[t] = float(closes[t])
    except Exception as e:
        st.warning(f"Price error: {e}")
    return result


@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=86400)
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
    return pd.DataFrame(frames) if frames else pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_fundamentals(tickers: tuple) -> pd.DataFrame:
    rows = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            rows[ticker] = {
                "Name":           info.get("longName", ticker),
                "Dividend Yield": info.get("dividendYield"),
                "Payout Ratio":   info.get("payoutRatio"),
                "ROE":            info.get("returnOnEquity"),
                "Revenue Growth": info.get("revenueGrowth"),
                "EPS Growth":     info.get("earningsGrowth"),
                "Profit Margin":  info.get("profitMargins"),
                "Debt/Equity":    info.get("debtToEquity"),
                "Forward P/E":    info.get("forwardPE"),
                "FCF":            info.get("freeCashflow"),
                "Market Cap":     info.get("marketCap"),
                "Beta":           info.get("beta"),
                "Analyst Target": info.get("targetMeanPrice"),
            }
            time.sleep(0.3)
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

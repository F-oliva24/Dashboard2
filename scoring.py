"""
scoring.py — Score quantitativi per 5 categorie di asset.
"""
import numpy as np
import pandas as pd
import streamlit as st
from data import fetch_prices, fetch_fundamentals, fetch_dividends


def rank_norm(s: pd.Series, asc: bool = True) -> pd.Series:
    if s.isna().all():
        return pd.Series(0.5, index=s.index)
    r = s.rank(ascending=asc, na_option="bottom")
    return (r - 1) / max(r.max() - 1, 1)


def score_etf(prices: pd.DataFrame, names: dict) -> pd.DataFrame:
    rows = []
    for t in prices.columns:
        s = prices[t].dropna()
        if len(s) < 60: continue
        ret = s.pct_change().dropna()
        m12 = (s.iloc[-1]/s.iloc[max(0,len(s)-252)]-1) if len(s)>252 else np.nan
        m6  = (s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        m3  = (s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1)  if len(s)>63  else np.nan
        r1y = ret.iloc[-252:] if len(ret)>=252 else ret
        vol = r1y.std()*np.sqrt(252)
        sh  = (r1y.mean()*252)/vol if vol>0 else np.nan
        rows.append({"Ticker":t,"Name":names.get(t,t),
                     "Return 12M":m12,"Return 6M":m6,"Return 3M":m3,
                     "Annual Vol":vol,"Sharpe 1Y":sh})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"] = (0.30*rank_norm(df["Return 12M"]) + 0.20*rank_norm(df["Return 6M"]) +
                   0.15*rank_norm(df["Return 3M"])   + 0.15*rank_norm(df["Annual Vol"],False) +
                   0.20*rank_norm(df["Sharpe 1Y"]))
    return df.sort_values("Score", ascending=False)


def score_dividend(prices, names, fund, divs) -> pd.DataFrame:
    rows = []
    for t in prices.columns:
        s = prices[t].dropna()
        if len(s)<60 or t not in fund.index: continue
        f  = fund.loc[t]
        dv = divs.get(t, pd.Series(dtype=float))
        dg, dy = np.nan, 0
        if dv is not None and len(dv)>1:
            try:
                ann = dv.resample("YE").sum(); ann = ann[ann>0]
                if len(ann)>=2:
                    n = min(5,len(ann)-1)
                    dg = (ann.iloc[-1]/ann.iloc[-(n+1)])**(1/n)-1
                dy = sum(1 for v in reversed(ann.values) if v>0)
            except: pass
        fcf = np.nan
        if pd.notna(f.get("FCF")) and pd.notna(f.get("Market Cap")) and f["Market Cap"]>0:
            fcf = f["FCF"]/f["Market Cap"]
        rows.append({"Ticker":t,"Name":names.get(t,str(f.get("Name",t))),
                     "Dividend Yield":f.get("Dividend Yield"),"Payout Ratio":f.get("Payout Ratio"),
                     "Div Growth 5Y":dg,"Consec. Years":dy,"FCF Yield":fcf,
                     "Debt/Equity":f.get("Debt/Equity")})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"] = (0.25*rank_norm(df["Dividend Yield"]) + 0.20*rank_norm(df["Payout Ratio"],False) +
                   0.20*rank_norm(df["Div Growth 5Y"])   + 0.15*rank_norm(df["Consec. Years"]) +
                   0.10*rank_norm(df["FCF Yield"])        + 0.10*rank_norm(df["Debt/Equity"],False))
    return df.sort_values("Score", ascending=False)


def score_growth(prices, names, fund) -> pd.DataFrame:
    rows = []
    for t in prices.columns:
        s = prices[t].dropna()
        if len(s)<60 or t not in fund.index: continue
        f  = fund.loc[t]
        m6 = (s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        ups = np.nan
        if pd.notna(f.get("Analyst Target")) and s.iloc[-1]>0:
            ups = (f["Analyst Target"]-s.iloc[-1])/s.iloc[-1]
        rows.append({"Ticker":t,"Name":names.get(t,str(f.get("Name",t))),
                     "Revenue Growth":f.get("Revenue Growth"),"EPS Growth":f.get("EPS Growth"),
                     "ROE":f.get("ROE"),"Profit Margin":f.get("Profit Margin"),
                     "Momentum 6M":m6,"Analyst Upside":ups,"Forward P/E":f.get("Forward P/E")})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"] = (0.25*rank_norm(df["Revenue Growth"]) + 0.20*rank_norm(df["EPS Growth"]) +
                   0.20*rank_norm(df["ROE"])             + 0.15*rank_norm(df["Profit Margin"]) +
                   0.10*rank_norm(df["Momentum 6M"])     + 0.10*rank_norm(df["Analyst Upside"]))
    return df.sort_values("Score", ascending=False)


def score_macro(prices, names) -> pd.DataFrame:
    rows = []
    for t in prices.columns:
        s = prices[t].dropna()
        if len(s)<30: continue
        ret = s.pct_change().dropna()
        m3  = (s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1)  if len(s)>63  else np.nan
        m1  = (s.iloc[-1]/s.iloc[max(0,len(s)-21)]-1)  if len(s)>21  else np.nan
        r6  = ret.iloc[-126:] if len(ret)>=126 else ret
        vol = ret.iloc[-63:].std()*np.sqrt(252) if len(ret)>=63 else ret.std()*np.sqrt(252)
        sh  = (r6.mean()*252)/(r6.std()*np.sqrt(252)) if r6.std()>0 else np.nan
        rows.append({"Ticker":t,"Name":names.get(t,t),
                     "Momentum 3M":m3,"Momentum 1M":m1,"Sharpe 6M":sh,"Volatility 3M":vol})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"] = (0.35*rank_norm(df["Momentum 3M"])    + 0.25*rank_norm(df["Momentum 1M"]) +
                   0.25*rank_norm(df["Sharpe 6M"])       + 0.15*rank_norm(df["Volatility 3M"],False))
    return df.sort_values("Score", ascending=False)


def compute_scores(category: str, names: dict) -> pd.DataFrame:
    """Entry point unificato — scarica prezzi e calcola score per categoria."""
    tickers = tuple(sorted(names.keys()))
    prices  = fetch_prices(tickers, "3y")
    valid   = [t for t in tickers if t in prices.columns]
    if not valid:
        return pd.DataFrame()

    if category in ["UCITS Accumulation", "ETF Accumulation"]:
        return score_etf(prices[valid], names)
    elif category == "Dividend Stocks":
        fund = fetch_fundamentals(tickers)
        divs = fetch_dividends(tickers)
        return score_dividend(prices[valid], names, fund, divs)
    elif category == "Growth Stocks":
        fund = fetch_fundamentals(tickers)
        return score_growth(prices[valid], names, fund)
    else:
        return score_macro(prices[valid], names)

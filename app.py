

import json
import time
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf
from scipy import stats

# ------------------------------------------------------------------ #
#  PAGE CONFIG
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
#  CONSTANTS
# ------------------------------------------------------------------ #

BUDGET_DEFAULT    = 1450.0
GUEST_HOURS       = 1
PORTFOLIO_CACHE   = Path("last_portfolio.json")

# Known ISIN → Yahoo ticker + currency mapping
ISIN_MAP = {
    "IE00BKM4GZ66": {"ticker": "EIMI.L",  "currency": "USD", "name": "iShares Core MSCI EM IMI"},
    "IE000YYE6WK5": {"ticker": "DFNS.SW", "currency": "CHF", "name": "VanEck Defense ETF"},
    "IE00BK5BQT80": {"ticker": "VWCE.DE", "currency": "EUR", "name": "Vanguard FTSE All-World"},
    "IE00B4L5Y983": {"ticker": "IWDA.AS", "currency": "USD", "name": "iShares Core MSCI World"},
    "IE0031442068": {"ticker": "CSPX.L",  "currency": "USD", "name": "iShares Core S&P 500"},
    "IE00B52MJY50": {"ticker": "VUSA.AS", "currency": "USD", "name": "Vanguard S&P 500"},
    "IE00B3XXRP09": {"ticker": "VWRL.AS", "currency": "USD", "name": "Vanguard FTSE All-World Dist"},
}

# Vivid color palette
C = {
    "blue":   "#00B4FF", "green":  "#00FF94", "red":    "#FF3B3B",
    "orange": "#FF9500", "purple": "#BF5FFF", "teal":   "#00FFD1",
    "yellow": "#FFE600", "pink":   "#FF2D9B", "muted":  "#6B7280",
    "bg":     "#000000", "card":   "#0D0D0D", "border": "#1F1F1F",
    "text":   "#FFFFFF",
}
CHART_COLORS = ["#00B4FF","#00FF94","#FF9500","#BF5FFF","#FF3B3B","#00FFD1","#FFE600","#FF2D9B"]

UNIVERSE = {
    "UCITS Accumulation": {
        "VWCE.DE":"Vanguard FTSE All-World Acc","IWDA.AS":"iShares Core MSCI World Acc",
        "CSPX.L":"iShares Core S&P 500 Acc","EUNL.DE":"iShares Core MSCI World EUR",
        "IEMA.AS":"iShares Core MSCI EM IMI Acc","SPPW.DE":"SPDR MSCI World Acc",
        "VUSA.AS":"Vanguard S&P 500 Acc","XDWD.DE":"Xtrackers MSCI World Acc",
        "IUSQ.DE":"iShares MSCI ACWI Acc","MEUD.PA":"Amundi MSCI Europe Acc",
    },
    "ETF Accumulation": {
        "QQQ":"Invesco QQQ Nasdaq 100","VTI":"Vanguard Total Stock Market",
        "VGT":"Vanguard Info Technology","SCHD":"Schwab US Dividend Equity",
        "GLD":"SPDR Gold Shares","TLT":"iShares 20+ Year Treasury",
        "QUAL":"iShares MSCI USA Quality","MTUM":"iShares MSCI USA Momentum",
        "IGSB":"iShares Short-Term Corp Bond","IBIT":"iShares Bitcoin Trust",
    },
    "Dividend Stocks": {
        "JNJ":"Johnson & Johnson","PG":"Procter & Gamble","KO":"Coca-Cola",
        "ABBV":"AbbVie","MO":"Altria Group","T":"AT&T","VZ":"Verizon",
        "O":"Realty Income","ENB":"Enbridge","MCD":"McDonald's",
    },
    "Growth Stocks": {
        "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","GOOGL":"Alphabet",
        "META":"Meta Platforms","AMZN":"Amazon","ASML":"ASML Holding",
        "V":"Visa","UNH":"UnitedHealth","LLY":"Eli Lilly",
    },
    "Macro Assets": {
        "GLD":"Gold ETF","SLV":"Silver ETF","TLT":"Long-term Treasuries",
        "SHY":"Short-term Treasuries","XLE":"Energy Select SPDR",
        "XLU":"Utilities Select SPDR","XLF":"Financials Select SPDR",
        "DBA":"Invesco Agriculture","UUP":"USD Bull ETF","EEM":"iShares MSCI EM",
    },
}

FRED_SERIES = {
    "Fed Funds Rate":"FEDFUNDS","Yield Curve 10-2":"T10Y2Y",
    "VIX":"VIXCLS","10Y Treasury":"GS10","US CPI":"CPIAUCSL","EUR/USD":"DEXUSEU",
}

# ------------------------------------------------------------------ #
#  CSS
# ------------------------------------------------------------------ #

st.markdown(f"""
<style>
  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stApp"], section.main, .stMainBlockContainer {{
    background-color: {C['bg']} !important; color: {C['text']} !important;
  }}
  [data-testid="stSidebar"] {{
    background-color: #080808 !important;
    border-right: 1px solid {C['border']} !important;
  }}
  h1,h2,h3,h4,h5,h6,p,label,.stMarkdown {{ color: {C['text']} !important; }}
  [data-testid="stTabs"] button {{
    color: {C['muted']} !important; background: transparent !important;
    border-bottom: 2px solid transparent !important;
  }}
  [data-testid="stTabs"] button[aria-selected="true"] {{
    color: {C['blue']} !important; border-bottom: 2px solid {C['blue']} !important;
  }}
  input, textarea {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #333 !important; border-radius: 6px !important;
  }}
  [data-testid="stNumberInput"] button {{
    background-color: #2a2a2a !important; color: {C['text']} !important;
    border: 1px solid #333 !important;
  }}
  [data-testid="stNumberInput"] button:hover {{
    background-color: {C['blue']} !important; color: #000 !important;
  }}
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stMultiSelect"] > div > div {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #333 !important;
  }}
  [data-testid="stSelectbox"] svg {{ fill: {C['text']} !important; }}
  div[role="option"] {{ background-color: #1a1a1a !important; color: {C['text']} !important; }}
  div[role="option"]:hover {{ background-color: {C['blue']}33 !important; color: {C['blue']} !important; }}
  [data-testid="baseButton-primary"] {{
    background-color: {C['blue']} !important; color: #000 !important;
    font-weight: 700 !important; border: none !important;
  }}
  [data-testid="baseButton-primary"]:hover {{ background-color: #00d4ff !important; }}
  button:not([data-testid="baseButton-primary"]) {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #444 !important;
  }}
  button:not([data-testid="baseButton-primary"]):hover {{
    background-color: #2a2a2a !important; border-color: {C['blue']} !important;
    color: {C['blue']} !important;
  }}
  [data-testid="stExpander"] {{
    background-color: #0D0D0D !important; border: 1px solid {C['border']} !important;
    border-radius: 8px !important;
  }}
  [data-testid="stExpander"] summary {{ color: {C['text']} !important; }}
  [data-testid="stExpander"] summary:hover {{ color: {C['blue']} !important; }}
  [data-testid="stDataFrame"] {{ background-color: {C['card']} !important; }}
  .stCaption, small {{ color: {C['muted']} !important; }}
  [data-testid="stAlert"] {{
    background-color: #111 !important; border: 1px solid #333 !important;
    color: {C['text']} !important;
  }}
  [data-testid="stFileUploader"] {{
    background-color: #0D0D0D !important; border: 1px dashed #444 !important;
    border-radius: 10px !important;
  }}
  hr {{ border-color: {C['border']} !important; }}
  .kpi-box {{
    background: {C['card']}; border: 1px solid {C['border']};
    border-radius: 12px; padding: 18px 22px; margin-bottom: 10px;
  }}
  .kpi-label {{
    font-size: 11px; color: {C['muted']}; text-transform: uppercase;
    letter-spacing: .08em; margin-bottom: 6px;
  }}
  .kpi-value {{ font-size: 24px; font-weight: 800; letter-spacing: -.01em; }}
  .section-title {{
    font-size: 11px; font-weight: 600; color: {C['muted']};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 28px 0 14px; border-bottom: 1px solid {C['border']}; padding-bottom: 8px;
  }}
  .badge-admin {{
    display:inline-block; background:{C['green']}22; color:{C['green']};
    border:1px solid {C['green']}55; border-radius:20px; padding:3px 12px;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em;
  }}
  .badge-guest {{
    display:inline-block; background:{C['orange']}22; color:{C['orange']};
    border:1px solid {C['orange']}55; border-radius:20px; padding:3px 12px;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em;
  }}
  .upload-hint {{
    background:{C['card']}; border:1px dashed #444; border-radius:12px;
    padding:32px; text-align:center; color:{C['muted']}; font-size:14px;
  }}
  .scenario-card {{
    background:{C['card']}; border:1px solid {C['border']}; border-radius:12px;
    padding:20px; margin-bottom:16px;
  }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
    font=dict(color=C["text"], family="Inter, system-ui, sans-serif", size=12),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"]),
)

def apply_layout(fig, title="", height=380):
    fig.update_layout(**PLOTLY_LAYOUT, height=height,
        title=dict(text=title, font=dict(size=13, color=C["text"])))
    fig.update_xaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    fig.update_yaxes(gridcolor=C["border"], linecolor=C["border"], zeroline=False)
    return fig

def kpi(label, value, color):
    st.markdown(f'<div class="kpi-box"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value" style="color:{color}">{value}</div></div>',
                unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  AUTH
# ------------------------------------------------------------------ #

def gen_guest_pw(n=10):
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(n))

def get_admin_pw():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except:
        return "admin123"

def check_auth():
    if "auth_role" not in st.session_state:
        return None
    if st.session_state["auth_role"] == "guest":
        exp = st.session_state.get("guest_expiry")
        if exp and datetime.now() > exp:
            st.session_state.pop("auth_role", None)
            return None
    return st.session_state["auth_role"]

def render_login():
    st.markdown(f"""
    <div style="max-width:420px;margin:80px auto;background:{C['card']};
                border:1px solid {C['border']};border-radius:16px;padding:40px;text-align:center">
      <div style="font-size:28px;font-weight:800;margin-bottom:8px">📈 Investment Dashboard</div>
      <div style="color:{C['muted']};font-size:13px;margin-bottom:28px">Enter your password to continue</div>
    </div>
    """, unsafe_allow_html=True)
    col = st.columns([1,2,1])[1]
    with col:
        pw = st.text_input("Password", type="password", placeholder="Enter password...")
        if st.button("Access Dashboard", type="primary", use_container_width=True):
            guest_pw  = st.session_state.get("guest_password")
            guest_exp = st.session_state.get("guest_expiry")
            if pw == get_admin_pw():
                st.session_state["auth_role"] = "admin"
                st.rerun()
            elif guest_pw and pw == guest_pw and guest_exp and datetime.now() < guest_exp:
                st.session_state["auth_role"] = "guest"
                st.rerun()
            else:
                st.error("Wrong password or expired guest access.")

def render_auth_sidebar(is_admin):
    if is_admin:
        st.sidebar.markdown('<span class="badge-admin">⚡ Admin</span>', unsafe_allow_html=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Guest Access**")
        if st.sidebar.button("🔑 Generate Guest Password"):
            pw  = gen_guest_pw()
            exp = datetime.now() + timedelta(hours=GUEST_HOURS)
            st.session_state["guest_password"] = pw
            st.session_state["guest_expiry"]   = exp
            st.sidebar.success(f"Password: `{pw}`")
            st.sidebar.caption(f"Expires at {exp.strftime('%H:%M')} ({GUEST_HOURS}h)")
        if st.session_state.get("guest_password"):
            exp = st.session_state.get("guest_expiry")
            if exp and datetime.now() < exp:
                rem = int((exp - datetime.now()).seconds / 60)
                st.sidebar.info(f"Active: `{st.session_state['guest_password']}` — {rem} min left")
    else:
        st.sidebar.markdown('<span class="badge-guest">👁 Guest (read-only)</span>', unsafe_allow_html=True)
        exp = st.session_state.get("guest_expiry")
        if exp:
            rem = max(0, int((exp - datetime.now()).seconds / 60))
            st.sidebar.caption(f"Session expires in {rem} min")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("auth_role", None)
        st.rerun()

# ------------------------------------------------------------------ #
#  DATA FETCHING
# ------------------------------------------------------------------ #

@st.cache_data(ttl=3600)
def fetch_prices(tickers: tuple, period="3y") -> pd.DataFrame:
    data = yf.download(list(tickers), period=period, auto_adjust=True,
                       progress=False, threads=True)
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"].dropna(how="all")
    return data[["Close"]].rename(columns={"Close": tickers[0]}).dropna(how="all")

@st.cache_data(ttl=3600)
def fetch_current_prices(tickers: tuple) -> dict:
    result = {}
    try:
        data = yf.download(list(tickers), period="5d", auto_adjust=True, progress=False)
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
    for cur, pair in {"USD":"EURUSD=X","CHF":"EURCHF=X","GBP":"EURGBP=X"}.items():
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
                "Name": info.get("longName", ticker),
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

# ------------------------------------------------------------------ #
#  DEGIRO CSV PARSER
# ------------------------------------------------------------------ #

def parse_degiro_csv(uploaded_file) -> tuple[pd.DataFrame, list]:
    """
    Parse DEGIRO portfolio CSV — keeps ALL columns.
    Returns (positions_df, unmapped_isins)

    Columns preserved from CSV:
        name          — full product name (Prodotto)
        isin          — ISIN code (Codice)
        qty           — quantity (Quantità)
        degiro_price  — last price from DEGIRO (Ultimo)
        degiro_currency — currency of the position
        degiro_value  — local value (Valore)
        degiro_value_eur — value in EUR from DEGIRO (Valore in EUR)

    Added by app:
        ticker        — Yahoo Finance ticker (from ISIN_MAP)
        currency      — currency for yfinance pricing
        yf_name       — friendly name from ISIN_MAP
    """
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Rename all known DEGIRO columns (IT and EN)
        col_map = {
            "Prodotto":       "name",
            "Product":        "name",
            "Codice":         "isin",
            "Symbol/ISIN":    "isin",
            "Quantità":       "qty",
            "Quantity":       "qty",
            "Ultimo":         "degiro_price",
            "Last":           "degiro_price",
            "Valore in EUR":  "degiro_value_eur",
            "Value in EUR":   "degiro_value_eur",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Handle the unnamed currency column and value column
        # DEGIRO CSV has: ..., Valore, <unnamed>, Valore in EUR
        # The unnamed column is the currency, Valore is the local value
        cols = df.columns.tolist()
        unnamed = [c for c in cols if c.startswith("Unnamed")]
        if unnamed:
            df = df.rename(columns={unnamed[0]: "degiro_currency_raw"})

        # Find Valore / Value column (local value before EUR conversion)
        for c in cols:
            if c in ["Valore", "Value", "Local value"] and c not in col_map:
                df = df.rename(columns={c: "degiro_value_local"})
                break

        # Clean qty — read as-is, already integer
        if "qty" in df.columns:
            df["qty"] = pd.to_numeric(df["qty"], errors="coerce")

        # Clean price/value columns — comma decimal separator
        def clean_num(series):
            return pd.to_numeric(
                series.astype(str)
                      .str.replace('"', '', regex=False)
                      .str.replace('€', '', regex=False)
                      .str.strip()
                      .str.replace(',', '.', regex=False),
                errors="coerce"
            )

        for col in ["degiro_price","degiro_value_eur","degiro_value_local"]:
            if col in df.columns:
                df[col] = clean_num(df[col])

        # Extract currency from the raw currency column or from degiro_currency_raw
        if "degiro_currency_raw" in df.columns:
            df["degiro_currency"] = df["degiro_currency_raw"].astype(str).str.strip()
        else:
            df["degiro_currency"] = "EUR"

        # Drop cash rows and rows without ISIN
        df = df.dropna(subset=["isin"])
        df = df[~df["isin"].astype(str).str.upper().str.contains("CASH|FUND|FTX", na=False)]
        df = df[df["qty"].notna() & (df["qty"] > 0)]
        df = df.reset_index(drop=True)

        # Map ISIN → Yahoo ticker + currency
        unmapped = []
        tickers, currencies, yf_names = [], [], []
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
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame(), []

# ------------------------------------------------------------------ #
#  PORTFOLIO METRICS
# ------------------------------------------------------------------ #

def calc_portfolio(positions_df: pd.DataFrame, current_prices: dict,
                   fx_rates: dict) -> tuple[pd.DataFrame, float]:
    """
    Calcola metriche portafoglio.
    - degiro_price = prezzo di chiusura DEGIRO (usato come prezzo di carico)
    - current_prices = prezzi live da yfinance
    - P&L calcolato in valuta originale
    - Valore totale in EUR
    """
    rows = []
    total_value = 0.0

    for _, pos in positions_df.iterrows():
        ticker      = pos.get("ticker")
        qty         = float(pos["qty"])
        degiro_px   = float(pos["degiro_price"]) if pd.notna(pos.get("degiro_price")) else 0
        currency    = pos.get("currency", "EUR")
        fx          = fx_rates.get(currency, 1.0)
        curr_px     = current_prices.get(ticker) if ticker else None
        deg_val_eur = pos.get("degiro_value_eur")
        deg_currency= pos.get("degiro_currency", currency)

        cost_orig = qty * degiro_px
        val_orig  = qty * curr_px if curr_px else None
        pl_orig   = (val_orig - cost_orig) if val_orig is not None else None
        pl_pct    = (pl_orig / cost_orig) if (pl_orig is not None and cost_orig > 0) else None

        val_eur  = val_orig * fx if val_orig is not None else cost_orig * fx
        pl_eur   = pl_orig  * fx if pl_orig  is not None else None
        cost_eur = cost_orig * fx

        total_value += val_eur

        rows.append({
            "Ticker":             ticker or pos.get("isin", "N/A"),
            "Name":               str(pos.get("yf_name", pos.get("name", ""))),
            "ISIN":               str(pos.get("isin", "")),
            "Currency":           deg_currency,
            "Qty":                qty,
            "DEGIRO Price":       f"{degiro_px:.2f} {deg_currency}" if degiro_px else "N/A",
            "Current Price (YF)": f"{curr_px:.2f} {currency}" if curr_px else "N/A",
            "Value (orig)":       f"{val_orig:,.2f} {currency}" if val_orig else "N/A",
            "P&L (orig)":         f"{pl_orig:+,.2f} {currency}" if pl_orig is not None else "N/A",
            "P&L (%)":            pl_pct,
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

def calc_risk(port_ret: pd.Series, total_value: float, conf=0.95, h=1) -> dict:
    q      = 1 - conf
    var_h  = -np.percentile(port_ret, q*100) * np.sqrt(h)
    tail   = port_ret[port_ret <= np.percentile(port_ret, q*100)]
    cvar_h = -tail.mean() * np.sqrt(h) if len(tail) > 0 else var_h
    mu,sig = port_ret.mean(), port_ret.std()
    var_p  = -(mu*h + stats.norm.ppf(q)*sig*np.sqrt(h))
    ann    = (1+port_ret).prod()**(252/max(len(port_ret),1)) - 1
    vol    = sig * np.sqrt(252)
    sh     = ann/vol if vol>0 else np.nan
    down   = port_ret[port_ret < 0]
    so     = ann/(down.std()*np.sqrt(252)) if len(down)>0 else np.nan
    cum    = (1+port_ret).cumprod()
    dd     = (cum - cum.expanding().max()) / cum.expanding().max()
    return {
        "annual_return":ann,"volatility":vol,"sharpe":sh,"sortino":so,
        "max_drawdown":dd.min(),"hit_rate":(port_ret>0).mean(),
        "var_hist_pct":var_h,"var_hist_eur":var_h*total_value,
        "cvar_hist_eur":cvar_h*total_value,
        "var_para_pct":var_p,"var_para_eur":var_p*total_value,
        "drawdown_series":dd,"cumulative_returns":cum,
    }

# ------------------------------------------------------------------ #
#  SCORING
# ------------------------------------------------------------------ #

def rank_norm(s, asc=True):
    if s.isna().all(): return pd.Series(0.5, index=s.index)
    r = s.rank(ascending=asc, na_option="bottom")
    return (r-1)/max(r.max()-1,1)

def score_etf(prices, names):
    rows=[]
    for t in prices.columns:
        s=prices[t].dropna()
        if len(s)<60: continue
        ret=s.pct_change().dropna()
        m12=(s.iloc[-1]/s.iloc[max(0,len(s)-252)]-1) if len(s)>252 else np.nan
        m6=(s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        m3=(s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1) if len(s)>63 else np.nan
        r1y=ret.iloc[-252:] if len(ret)>=252 else ret
        vol=r1y.std()*np.sqrt(252); sh=(r1y.mean()*252)/vol if vol>0 else np.nan
        rows.append({"Ticker":t,"Name":names.get(t,t),"Return 12M":m12,
                     "Return 6M":m6,"Return 3M":m3,"Annual Vol":vol,"Sharpe 1Y":sh})
    df=pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"]=(0.30*rank_norm(df["Return 12M"])+0.20*rank_norm(df["Return 6M"])+
                 0.15*rank_norm(df["Return 3M"])+0.15*rank_norm(df["Annual Vol"],False)+
                 0.20*rank_norm(df["Sharpe 1Y"]))
    return df.sort_values("Score",ascending=False)

def score_dividend(prices, names, fund, divs):
    rows=[]
    for t in prices.columns:
        s=prices[t].dropna()
        if len(s)<60 or t not in fund.index: continue
        f=fund.loc[t]
        dv=divs.get(t,pd.Series(dtype=float))
        dg,dy=np.nan,0
        if dv is not None and len(dv)>1:
            try:
                ann=dv.resample("YE").sum(); ann=ann[ann>0]
                if len(ann)>=2:
                    n=min(5,len(ann)-1); dg=(ann.iloc[-1]/ann.iloc[-(n+1)])**(1/n)-1
                dy=sum(1 for v in reversed(ann.values) if v>0)
            except: pass
        fcf=np.nan
        if pd.notna(f.get("FCF")) and pd.notna(f.get("Market Cap")) and f["Market Cap"]>0:
            fcf=f["FCF"]/f["Market Cap"]
        rows.append({"Ticker":t,"Name":names.get(t,str(f.get("Name",t))),
                     "Dividend Yield":f.get("Dividend Yield"),"Payout Ratio":f.get("Payout Ratio"),
                     "Div Growth 5Y":dg,"Consec. Years":dy,"FCF Yield":fcf,"Debt/Equity":f.get("Debt/Equity")})
    df=pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"]=(0.25*rank_norm(df["Dividend Yield"])+0.20*rank_norm(df["Payout Ratio"],False)+
                 0.20*rank_norm(df["Div Growth 5Y"])+0.15*rank_norm(df["Consec. Years"])+
                 0.10*rank_norm(df["FCF Yield"])+0.10*rank_norm(df["Debt/Equity"],False))
    return df.sort_values("Score",ascending=False)

def score_growth(prices, names, fund):
    rows=[]
    for t in prices.columns:
        s=prices[t].dropna()
        if len(s)<60 or t not in fund.index: continue
        f=fund.loc[t]
        m6=(s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        ups=np.nan
        if pd.notna(f.get("Analyst Target")) and s.iloc[-1]>0:
            ups=(f["Analyst Target"]-s.iloc[-1])/s.iloc[-1]
        rows.append({"Ticker":t,"Name":names.get(t,str(f.get("Name",t))),
                     "Revenue Growth":f.get("Revenue Growth"),"EPS Growth":f.get("EPS Growth"),
                     "ROE":f.get("ROE"),"Profit Margin":f.get("Profit Margin"),
                     "Momentum 6M":m6,"Analyst Upside":ups,"Forward P/E":f.get("Forward P/E")})
    df=pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"]=(0.25*rank_norm(df["Revenue Growth"])+0.20*rank_norm(df["EPS Growth"])+
                 0.20*rank_norm(df["ROE"])+0.15*rank_norm(df["Profit Margin"])+
                 0.10*rank_norm(df["Momentum 6M"])+0.10*rank_norm(df["Analyst Upside"]))
    return df.sort_values("Score",ascending=False)

def score_macro(prices, names):
    rows=[]
    for t in prices.columns:
        s=prices[t].dropna()
        if len(s)<30: continue
        ret=s.pct_change().dropna()
        m3=(s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1) if len(s)>63 else np.nan
        m1=(s.iloc[-1]/s.iloc[max(0,len(s)-21)]-1) if len(s)>21 else np.nan
        r6=ret.iloc[-126:] if len(ret)>=126 else ret
        vol=ret.iloc[-63:].std()*np.sqrt(252) if len(ret)>=63 else ret.std()*np.sqrt(252)
        sh=(r6.mean()*252)/(r6.std()*np.sqrt(252)) if r6.std()>0 else np.nan
        rows.append({"Ticker":t,"Name":names.get(t,t),
                     "Momentum 3M":m3,"Momentum 1M":m1,"Sharpe 6M":sh,"Volatility 3M":vol})
    df=pd.DataFrame(rows).set_index("Ticker")
    if df.empty: return df
    df["Score"]=(0.35*rank_norm(df["Momentum 3M"])+0.25*rank_norm(df["Momentum 1M"])+
                 0.25*rank_norm(df["Sharpe 6M"])+0.15*rank_norm(df["Volatility 3M"],False))
    return df.sort_values("Score",ascending=False)

# ------------------------------------------------------------------ #
#  SHARED RISK CHARTS
# ------------------------------------------------------------------ #

def render_risk_charts(port_ret, total_value):
    r95  = calc_risk(port_ret, total_value, 0.95, 1)
    r99  = calc_risk(port_ret, total_value, 0.99, 1)
    r95_5= calc_risk(port_ret, total_value, 0.95, 5)

    section("Performance")
    m1,m2,m3,m4 = st.columns(4)
    with m1: kpi("Annual Return", f"{r95['annual_return']:+.1%}",
                  C["green"] if r95["annual_return"]>=0 else C["red"])
    with m2: kpi("Sharpe Ratio",     f"{r95['sharpe']:.2f}",       C["teal"])
    with m3: kpi("Max Drawdown",      f"{r95['max_drawdown']:.1%}", C["red"])
    with m4: kpi("Annual Volatility", f"{r95['volatility']:.1%}",   C["orange"])

    section("Value at Risk")
    v1,v2,v3 = st.columns(3)
    with v1: kpi("VaR 95% — 1 day",  f"€{r95['var_hist_eur']:,.0f} ({r95['var_hist_pct']:.2%})",  C["orange"])
    with v2: kpi("VaR 99% — 1 day",  f"€{r99['var_hist_eur']:,.0f} ({r99['var_hist_pct']:.2%})",  C["red"])
    with v3: kpi("VaR 95% — 5 days", f"€{r95_5['var_hist_eur']:,.0f} ({r95_5['var_hist_pct']:.2%})", C["yellow"])

    cum_r = r95["cumulative_returns"]
    dd    = r95["drawdown_series"]
    fig_p = make_subplots(rows=2, cols=1, shared_xaxes=True,
                          row_heights=[0.65,0.35], vertical_spacing=0.04)
    fig_p.add_trace(go.Scatter(x=cum_r.index, y=(cum_r-1)*100, name="Cumulative Return %",
        fill="tozeroy", fillcolor="rgba(0,180,255,0.12)", line=dict(color=C["blue"],width=2),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"), row=1, col=1)
    fig_p.add_trace(go.Scatter(x=dd.index, y=dd.values*100, name="Drawdown %",
        fill="tozeroy", fillcolor="rgba(255,59,59,0.2)", line=dict(color=C["red"],width=1.5),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"), row=2, col=1)
    fig_p.update_layout(**PLOTLY_LAYOUT, height=440,
        title=dict(text="Cumulative Return & Drawdown", font=dict(size=13,color=C["text"])))
    fig_p.update_xaxes(gridcolor=C["border"]); fig_p.update_yaxes(gridcolor=C["border"])
    st.plotly_chart(fig_p, use_container_width=True)

    col_d, col_c = st.columns(2)
    with col_d:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(x=port_ret.values*100, nbinsx=60,
            marker_color=C["purple"], opacity=0.85))
        fig_dist.add_vline(x=-r95["var_hist_pct"]*100, line_color=C["orange"],
            line_width=2, line_dash="dash",
            annotation_text=f"VaR 95%: {r95['var_hist_pct']:.2%}",
            annotation_font_color=C["orange"])
        fig_dist.add_vline(x=-r99["var_hist_pct"]*100, line_color=C["red"],
            line_width=2, line_dash="dash",
            annotation_text=f"VaR 99%: {r99['var_hist_pct']:.2%}",
            annotation_font_color=C["red"])
        apply_layout(fig_dist, "Return Distribution + VaR", 380)
        st.plotly_chart(fig_dist, use_container_width=True)
    return r95

# ------------------------------------------------------------------ #
#  SCORE BAR CHART
# ------------------------------------------------------------------ #

def render_score_chart(df, title, color):
    if df.empty or "Score" not in df.columns:
        st.info("No data available."); return
    df2    = df[["Score"]].sort_values("Score", ascending=True)
    name_c = "Name" if "Name" in df.columns else None
    labels = [f"{t} — {df.loc[t,'Name'][:25]}" if name_c else t for t in df2.index]
    fig = go.Figure(go.Bar(
        y=labels, x=df2["Score"].values, orientation="h",
        marker_color=color, opacity=0.85,
        text=[f"{v:.2f}" for v in df2["Score"].values],
        textposition="outside", textfont=dict(color=C["text"]),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>"
    ))
    fig.add_vline(x=0.5, line_color=C["muted"], line_dash="dash",
                  annotation_text="0.5", annotation_font_color=C["muted"])
    fig.update_xaxes(range=[0,1.2])
    apply_layout(fig, title, 420)
    st.plotly_chart(fig, use_container_width=True)

# ================================================================== #
#  PAGE 1 — MY PORTFOLIO
# ================================================================== #

def page_portfolio(is_admin, budget):
    st.title("💼 My Portfolio")

    # Refresh buttons
    c1,c2,_ = st.columns([1,1,5])
    with c1:
        if st.button("🔄 Prices", type="primary"): st.cache_data.clear(); st.rerun()
    with c2:
        if st.button("🔄 All"): st.cache_data.clear(); st.rerun()

    # CSV Upload
    section("Upload DEGIRO Portfolio CSV")
    if is_admin:
        uploaded = st.file_uploader(
            "Drag & drop your DEGIRO CSV export here",
            type=["csv"], key="ptf_csv",
            help="DEGIRO → Portfolio → Export → CSV"
        )
        if uploaded:
            positions_df, unmapped = parse_degiro_csv(uploaded)
            if not positions_df.empty:
                # Save to session
                st.session_state["positions_df"] = positions_df
                # Cache to JSON for scenario builder
                positions_df.to_json(PORTFOLIO_CACHE, orient="records")

            if unmapped:
                st.warning(f"Unknown ISINs — map them manually: {unmapped}")
                for isin in unmapped:
                    col_t, col_c = st.columns(2)
                    with col_t:
                        t = st.text_input(f"Yahoo ticker for {isin}", key=f"map_{isin}")
                    with col_c:
                        c = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key=f"cur_{isin}")
                    if t:
                        ISIN_MAP[isin] = {"ticker": t.upper(), "currency": c, "name": isin}
    else:
        st.info("👁 Read-only mode — ask admin to upload the latest CSV.")

    # Load positions from session or cache
    positions_df = st.session_state.get("positions_df")
    if positions_df is None and PORTFOLIO_CACHE.exists():
        try:
            positions_df = pd.read_json(PORTFOLIO_CACHE, orient="records")
            st.session_state["positions_df"] = positions_df
        except:
            pass

    if positions_df is None or positions_df.empty:
        st.markdown('<div class="upload-hint">📂 Upload your DEGIRO CSV to see your portfolio metrics</div>',
                    unsafe_allow_html=True)
        return

    # Fetch prices
    valid_tickers = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
    if not valid_tickers:
        st.warning("No valid tickers found. Check ISIN mapping."); return

    with st.spinner("Loading prices..."):
        current_prices = fetch_current_prices(valid_tickers)
        fx_rates       = fetch_fx_rates()

    pivot, total_value = calc_portfolio(positions_df, current_prices, fx_rates)
    total_cost = pd.to_numeric(pivot["Cost (€)"], errors="coerce").sum()
    total_pl   = pd.to_numeric(pivot["P&L (€)"],  errors="coerce").sum()
    total_pl_pct = total_pl / total_cost if total_cost > 0 else 0

    # KPIs
    section("Overview")
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("Total Value",     f"€{total_value:,.0f}", C["blue"])
    with k2: kpi("Unrealised P&L",  f"€{total_pl:+,.0f} ({total_pl_pct:+.1%})",
                  C["green"] if total_pl>=0 else C["red"])
    with k3: kpi("Positions",       str(len(pivot)), C["teal"])
    with k4: kpi("Monthly Budget",  f"€{budget:,.0f}", C["purple"])

    # Positions table
    section("Positions")
    disp = pivot.drop(columns=["_val_orig","_pl_orig","Cost (€)","P&L (€)"], errors="ignore")
    disp["P&L (%)"] = disp["P&L (%)"].apply(lambda x: f"{x:+.2%}" if pd.notna(x) else "N/A")
    disp["Weight"]  = disp["Weight"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
    # Format EUR columns
    for col in ["Value (€) YF", "Value (€) DEGIRO", "P&L (€)", "Cost (€)"]:
        if col in disp.columns:
            disp[col] = disp[col].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
    st.dataframe(disp, use_container_width=True)

    # Charts
    section("Allocation & Budget")
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
        section("Monthly Budget Split")
        alloc_rows = []
        for ticker, row in pivot.iterrows():
            w       = float(row["Weight"]) if isinstance(row["Weight"], float) else 0
            bud     = budget * w
            curr_px = current_prices.get(ticker)
            cur     = str(row.get("Currency","EUR"))
            fx      = fx_rates.get(cur,1.0)
            p_eur   = curr_px * fx if curr_px else None
            qty_sug = bud / p_eur if p_eur else None
            alloc_rows.append({
                "Ticker": ticker, "Weight": f"{w:.1%}",
                "Budget (€)": f"€{bud:.2f}",
                "Price (€)": f"€{p_eur:.2f}" if p_eur else "N/A",
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
        hovertemplate="<b>%{x}</b><br>P&L (€): €%{y:+,.2f}<extra></extra>"
    ))
    fig_pl.add_hline(y=0, line_color=C["muted"], line_width=1)
    apply_layout(fig_pl, f"Unrealised P&L  |  Total: €{total_pl:+,.0f}", 340)
    st.plotly_chart(fig_pl, use_container_width=True)

    # Risk
    section("Risk Analysis")
    prices_ptf = fetch_prices(valid_tickers, "3y")
    valid_t    = [t for t in valid_tickers if t in prices_ptf.columns]
    if valid_t:
        w_raw  = {t: float(pivot.loc[t,"Value (€) YF"]) for t in valid_t
                  if t in pivot.index and pd.notna(pivot.loc[t,"Value (€) YF"])}
        w_tot  = sum(w_raw.values())
        w_norm = {t:v/w_tot for t,v in w_raw.items()} if w_tot>0 else {}
        if w_norm:
            w_arr    = np.array([w_norm[t] for t in valid_t if t in w_norm])
            ret_df   = prices_ptf[[t for t in valid_t if t in w_norm]].pct_change().dropna()
            port_ret = (ret_df * w_arr).sum(axis=1)
            r95 = render_risk_charts(port_ret, total_value)

            # Correlation
            corr = ret_df.corr()
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

# ================================================================== #
#  PAGE 2 — SCENARIO BUILDER
# ================================================================== #

def page_scenario(budget):
    st.title("🔬 Scenario Builder")
    st.caption("Simulate portfolio changes and compare with your real portfolio.")

    # Starting point toggle
    section("Starting Point")
    start_mode = st.radio(
        "Build scenario from:",
        ["🏦 Current portfolio", "⬜ From scratch"],
        horizontal=True, key="scenario_mode"
    )

    # Load base positions
    base_positions = {}
    if start_mode == "🏦 Current portfolio":
        positions_df = st.session_state.get("positions_df")
        if positions_df is not None and not positions_df.empty:
            for _, row in positions_df.iterrows():
                t = row.get("ticker")
                if t:
                    base_positions[t] = {
                        "ticker":    t,
                        "name":      str(row.get("yf_name", t)),
                        "qty":       float(row.get("qty", 0)),
                        "currency":  str(row.get("currency","EUR")),
                    }
            st.success(f"Loaded {len(base_positions)} positions from your current portfolio.")
        else:
            st.warning("No portfolio loaded. Upload your CSV in 'My Portfolio' first, "
                       "or switch to 'From scratch'.")

    # Init scenario positions in session
    if "scenario_positions" not in st.session_state or \
       st.session_state.get("scenario_mode_prev") != start_mode:
        st.session_state["scenario_positions"] = dict(base_positions)
        st.session_state["scenario_mode_prev"] = start_mode

    scenario = st.session_state["scenario_positions"]

    # Add assets from universe
    section("Add Assets to Scenario")
    all_universe_tickers = {}
    for cat, items in UNIVERSE.items():
        for t, n in items.items():
            all_universe_tickers[t] = f"{t} — {n} ({cat})"

    col_t, col_q, col_c = st.columns([2,1,1])
    with col_t:
        add_ticker = st.selectbox(
            "Select asset from universe",
            options=[""] + sorted(all_universe_tickers.keys()),
            format_func=lambda x: all_universe_tickers.get(x, x) if x else "— Select —",
            key="scen_add_ticker"
        )
    with col_q:
        add_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=0.5, key="scen_qty")
    with col_c:
        add_cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="scen_cur")

    if st.button("➕ Add to Scenario", type="primary") and add_ticker:
        scenario[add_ticker] = {
            "ticker":   add_ticker,
            "name":     all_universe_tickers.get(add_ticker, add_ticker),
            "qty":      add_qty,
            "currency": add_cur,
        }
        st.session_state["scenario_positions"] = scenario
        st.rerun()

    # Custom ticker
    with st.expander("Add custom ticker (not in universe)"):
        cc1,cc2,cc3 = st.columns([2,1,1])
        with cc1: custom_t = st.text_input("Yahoo ticker", key="custom_t").upper().strip()
        with cc2: custom_q = st.number_input("Qty", min_value=0.01, value=1.0, key="custom_q")
        with cc3: custom_c = st.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="custom_c")
        if st.button("➕ Add custom", key="btn_custom") and custom_t:
            scenario[custom_t] = {"ticker":custom_t,"name":custom_t,"qty":custom_q,"currency":custom_c}
            st.session_state["scenario_positions"] = scenario
            st.rerun()

    # Current scenario positions
    section("Scenario Positions")
    if not scenario:
        st.info("No positions yet. Add assets above.")
        return

    to_remove = []
    cols = st.columns(min(len(scenario), 4))
    for i, (ticker, pos) in enumerate(scenario.items()):
        with cols[i % len(cols)]:
            st.markdown(f'<div class="scenario-card">'
                        f'<b style="color:{CHART_COLORS[i%len(CHART_COLORS)]}">{ticker}</b><br>'
                        f'<small style="color:{C["muted"]}">{pos.get("name","")[:30]}</small>',
                        unsafe_allow_html=True)
            new_qty = st.number_input("Qty", min_value=0.0,
                                       value=float(pos.get("qty",1)),
                                       step=0.5, key=f"sq_{ticker}")
            scenario[ticker]["qty"] = new_qty
            if st.button("🗑", key=f"sr_{ticker}"):
                to_remove.append(ticker)
            st.markdown('</div>', unsafe_allow_html=True)

    for t in to_remove:
        del scenario[t]
        st.session_state["scenario_positions"] = scenario
        st.rerun()

    if not scenario:
        return

    # Fetch prices and compute scenario metrics
    section("Scenario Analysis")
    scen_tickers = tuple(sorted([t for t in scenario.keys()]))

    with st.spinner("Computing scenario metrics..."):
        curr_prices = fetch_current_prices(scen_tickers)
        fx_rates    = fetch_fx_rates()
        prices_scen = fetch_prices(scen_tickers, "3y")

    # Build positions_df for scenario
    scen_rows = []
    for t, pos in scenario.items():
        curr_px = curr_prices.get(t)
        cur     = pos.get("currency","EUR")
        fx      = fx_rates.get(cur,1.0)
        val_eur = pos["qty"] * curr_px * fx if curr_px else 0
        scen_rows.append({
            "ticker":     t,
            "qty":        pos["qty"],
            "last_price": curr_px or 0,
            "currency":   cur,
            "isin":       "",
            "yf_name":    pos.get("name", t),
        })
    scen_df   = pd.DataFrame(scen_rows)
    scen_pivot, scen_total = calc_portfolio(scen_df, curr_prices, fx_rates)

    # KPIs
    k1,k2,k3 = st.columns(3)
    with k1: kpi("Scenario Value", f"€{scen_total:,.0f}", C["blue"])
    with k2: kpi("Positions", str(len(scenario)), C["teal"])
    with k3: kpi("Budget for scenario", f"€{budget:,.0f}", C["purple"])

    # Allocation pie
    col_pie, col_alloc = st.columns(2)
    with col_pie:
        vals = pd.to_numeric(scen_pivot["Value (€)"], errors="coerce").fillna(0)
        fig_pie = go.Figure(go.Pie(
            labels=scen_pivot.index.tolist(), values=vals.tolist(), hole=0.45,
            textinfo="label+percent", textfont=dict(color=C["text"]),
            marker=dict(colors=CHART_COLORS),
            hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>"
        ))
        fig_pie.add_annotation(text=f"€{scen_total:,.0f}", x=0.5, y=0.5,
            font=dict(size=16, color=C["text"]), showarrow=False)
        apply_layout(fig_pie, "Scenario Allocation", 360)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_alloc:
        section("Budget Split")
        alloc_rows = []
        for ticker, row in scen_pivot.iterrows():
            w     = float(row["Weight"]) if isinstance(row["Weight"],float) else 0
            bud   = budget * w
            cp    = curr_prices.get(ticker)
            cur   = scenario.get(ticker,{}).get("currency","EUR")
            p_eur = cp * fx_rates.get(cur,1.0) if cp else None
            qty_s = bud / p_eur if p_eur else None
            alloc_rows.append({
                "Ticker": ticker, "Weight": f"{w:.1%}",
                "Budget (€)": f"€{bud:.2f}",
                "Price (€)": f"€{p_eur:.2f}" if p_eur else "N/A",
                "Units": f"{qty_s:.3f}" if qty_s else "N/A",
            })
        alloc_df = pd.DataFrame(alloc_rows)
        alloc_df.loc[len(alloc_df)] = ["TOTAL","100%",f"€{budget:.2f}","",""]
        st.dataframe(alloc_df.set_index("Ticker"), use_container_width=True)

    # Risk analysis
    valid_scen = [t for t in scen_tickers if t in prices_scen.columns]
    if valid_scen:
        w_raw  = {t: float(scen_pivot.loc[t,"Value (€)"]) for t in valid_scen
                  if t in scen_pivot.index and pd.notna(scen_pivot.loc[t,"Value (€)"])}
        w_tot  = sum(w_raw.values())
        w_norm = {t:v/w_tot for t,v in w_raw.items()} if w_tot>0 else {}
        if w_norm:
            w_arr    = np.array([w_norm[t] for t in valid_scen if t in w_norm])
            ret_df   = prices_scen[[t for t in valid_scen if t in w_norm]].pct_change().dropna()
            port_ret = (ret_df * w_arr).sum(axis=1)
            render_risk_charts(port_ret, scen_total)

            # Comparison vs real portfolio (if available)
            positions_df = st.session_state.get("positions_df")
            if positions_df is not None and not positions_df.empty and start_mode == "🏦 Current portfolio":
                section("Scenario vs Current Portfolio")
                real_tickers = tuple(sorted([t for t in positions_df["ticker"].dropna().unique()]))
                real_prices  = fetch_prices(real_tickers, "3y")
                real_curr    = fetch_current_prices(real_tickers)
                real_pivot, real_total = calc_portfolio(positions_df, real_curr, fx_rates)

                real_valid = [t for t in real_tickers if t in real_prices.columns]
                if real_valid:
                    rw_raw  = {t: float(real_pivot.loc[t,"Value (€)"]) for t in real_valid
                               if t in real_pivot.index and pd.notna(real_pivot.loc[t,"Value (€)"])}
                    rw_tot  = sum(rw_raw.values())
                    rw_norm = {t:v/rw_tot for t,v in rw_raw.items()} if rw_tot>0 else {}
                    if rw_norm:
                        rw_arr   = np.array([rw_norm[t] for t in real_valid if t in rw_norm])
                        rret_df  = real_prices[[t for t in real_valid if t in rw_norm]].pct_change().dropna()
                        real_ret = (rret_df * rw_arr).sum(axis=1)

                        r_real = calc_risk(real_ret, real_total, 0.95, 1)
                        r_scen = calc_risk(port_ret, scen_total, 0.95, 1)

                        comp_data = {
                            "Metric": ["Annual Return","Volatility","Sharpe","Max Drawdown","VaR 95% 1d"],
                            "Current": [
                                f"{r_real['annual_return']:+.2%}",
                                f"{r_real['volatility']:.2%}",
                                f"{r_real['sharpe']:.2f}",
                                f"{r_real['max_drawdown']:.2%}",
                                f"€{r_real['var_hist_eur']:,.0f} ({r_real['var_hist_pct']:.2%})",
                            ],
                            "Scenario": [
                                f"{r_scen['annual_return']:+.2%}",
                                f"{r_scen['volatility']:.2%}",
                                f"{r_scen['sharpe']:.2f}",
                                f"{r_scen['max_drawdown']:.2%}",
                                f"€{r_scen['var_hist_eur']:,.0f} ({r_scen['var_hist_pct']:.2%})",
                            ],
                        }
                        st.dataframe(pd.DataFrame(comp_data).set_index("Metric"),
                                     use_container_width=True)

# ================================================================== #
#  PAGE 3 — SCREENING
# ================================================================== #

def page_screening():
    st.title("🔍 Asset Screening")
    st.caption("Composite scores 0–1. Compare only within the same category.")

    cat_colors = {
        "UCITS Accumulation":C["blue"],"ETF Accumulation":C["green"],
        "Dividend Stocks":C["orange"],"Growth Stocks":C["purple"],"Macro Assets":C["teal"],
    }
    selected = st.selectbox("Select category", list(UNIVERSE.keys()))
    color    = cat_colors[selected]
    names    = UNIVERSE[selected]
    tickers  = tuple(sorted(names.keys()))

    with st.spinner(f"Loading {selected}..."):
        prices = fetch_prices(tickers,"3y")
        valid  = [t for t in tickers if t in prices.columns]
        if selected in ["UCITS Accumulation","ETF Accumulation"]:
            scores = score_etf(prices[valid], names)
        elif selected == "Dividend Stocks":
            fund = fetch_fundamentals(tickers)
            divs = fetch_dividends(tickers)
            scores = score_dividend(prices[valid], names, fund, divs)
        elif selected == "Growth Stocks":
            fund = fetch_fundamentals(tickers)
            scores = score_growth(prices[valid], names, fund)
        else:
            scores = score_macro(prices[valid], names)

    if not scores.empty:
        render_score_chart(scores, f"Composite Score — {selected}", color)
        section("Full Data Table")
        fmt = scores.copy()
        for col in fmt.columns:
            if col=="Name": continue
            elif col=="Score": fmt[col]=fmt[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
            elif any(k in col for k in ["Return","Growth","Yield","Margin","ROE","Vol","Momentum"]):
                fmt[col]=fmt[col].map(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
            else: fmt[col]=fmt[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        st.dataframe(fmt, use_container_width=True)
    else:
        st.warning("No data for this category.")

# ================================================================== #
#  PAGE 4 — MACRO
# ================================================================== #

def page_macro():
    st.title("🌍 Macroeconomic Context")
    macro = fetch_macro()
    if macro.empty:
        st.info("Macro data unavailable."); return

    latest = macro.ffill().iloc[-1]
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("Fed Funds Rate", f"{latest.get('Fed Funds Rate',float('nan')):.2f}%", C["blue"])
    with k2:
        yc = latest.get("Yield Curve 10-2", float("nan"))
        kpi("Yield Curve 10Y-2Y",
            f"{yc:.2f}%  {'⚠️ Inverted' if yc<0 else '✅ Normal'}",
            C["red"] if yc<0 else C["green"])
    with k3: kpi("VIX", f"{latest.get('VIX',float('nan')):.1f}", C["orange"])
    with k4: kpi("10Y Treasury", f"{latest.get('10Y Treasury',float('nan')):.2f}%", C["teal"])

    selected = st.multiselect("Select indicators",
                               options=macro.columns.tolist(),
                               default=macro.columns.tolist())
    if selected:
        cols = st.columns(2)
        for i, col_name in enumerate(selected):
            with cols[i%2]:
                s = macro[col_name].dropna().iloc[-10*12:]
                color = CHART_COLORS[i%len(CHART_COLORS)]
                r,g,b = (int(color[j:j+2],16) for j in (1,3,5))
                fig = go.Figure(go.Scatter(
                    x=s.index, y=s.values, fill="tozeroy",
                    fillcolor=f"rgba({r},{g},{b},0.12)",
                    line=dict(color=color, width=2),
                    hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"
                ))
                fig.add_annotation(text=f"  {s.iloc[-1]:.2f}", x=s.index[-1], y=s.iloc[-1],
                    font=dict(size=12, color=color), showarrow=False)
                apply_layout(fig, col_name, 280)
                st.plotly_chart(fig, use_container_width=True)

# ================================================================== #
#  MAIN
# ================================================================== #

def main():
    role = check_auth()
    if role is None:
        render_login()
        return

    is_admin = role == "admin"

    # Sidebar
    st.sidebar.title("📈 Investment Dashboard")
    render_auth_sidebar(is_admin)

    budget = st.sidebar.number_input(
        "Monthly Budget (€)", min_value=0.0,
        value=float(st.session_state.get("budget", BUDGET_DEFAULT)),
        step=50.0, format="%.0f"
    )
    st.session_state["budget"] = budget

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate", [
        "💼 My Portfolio",
        "🔬 Scenario Builder",
        "🔍 Screening",
        "🌍 Macro",
    ])

    if page == "💼 My Portfolio":
        page_portfolio(is_admin, budget)
    elif page == "🔬 Scenario Builder":
        page_scenario(budget)
    elif page == "🔍 Screening":
        page_screening()
    elif page == "🌍 Macro":
        page_macro()

    st.sidebar.markdown("---")
    st.sidebar.caption("Data: Yahoo Finance · FRED  |  ~15min delayed  |  Not financial advice.")

if __name__ == "__main__":
    main()

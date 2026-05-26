

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
#  CONFIG
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

PORTFOLIO_FILE = Path("portfolio.json")
BUDGET_DEFAULT = 1450.0
GUEST_DURATION_HOURS = 1

# Vivid colors on black
C = {
    "blue":    "#00B4FF",
    "green":   "#00FF94",
    "red":     "#FF3B3B",
    "orange":  "#FF9500",
    "purple":  "#BF5FFF",
    "teal":    "#00FFD1",
    "yellow":  "#FFE600",
    "pink":    "#FF2D9B",
    "muted":   "#6B7280",
    "bg":      "#000000",
    "card":    "#0D0D0D",
    "border":  "#1F1F1F",
    "text":    "#FFFFFF",
}

CHART_COLORS = [
    "#00B4FF", "#00FF94", "#FF9500", "#BF5FFF",
    "#FF3B3B", "#00FFD1", "#FFE600", "#FF2D9B",
]

UNIVERSE = {
    "UCITS Accumulation": {
        "VWCE.DE": "Vanguard FTSE All-World Acc",
        "IWDA.AS": "iShares Core MSCI World Acc",
        "CSPX.L":  "iShares Core S&P 500 Acc",
        "EUNL.DE": "iShares Core MSCI World EUR",
        "IEMA.AS": "iShares Core MSCI EM IMI Acc",
        "SPPW.DE": "SPDR MSCI World Acc",
        "VUSA.AS": "Vanguard S&P 500 Acc",
        "XDWD.DE": "Xtrackers MSCI World Acc",
        "IUSQ.DE": "iShares MSCI ACWI Acc",
        "MEUD.PA": "Amundi MSCI Europe Acc",
    },
    "ETF Accumulation": {
        "QQQ":  "Invesco QQQ Nasdaq 100",
        "VTI":  "Vanguard Total Stock Market",
        "VGT":  "Vanguard Info Technology",
        "SCHD": "Schwab US Dividend Equity",
        "GLD":  "SPDR Gold Shares",
        "TLT":  "iShares 20+ Year Treasury",
        "QUAL": "iShares MSCI USA Quality",
        "MTUM": "iShares MSCI USA Momentum",
        "IGSB": "iShares Short-Term Corp Bond",
        "IBIT": "iShares Bitcoin Trust",
    },
    "Dividend Stocks": {
        "JNJ":  "Johnson & Johnson",
        "PG":   "Procter & Gamble",
        "KO":   "Coca-Cola",
        "ABBV": "AbbVie",
        "MO":   "Altria Group",
        "T":    "AT&T",
        "VZ":   "Verizon",
        "O":    "Realty Income",
        "ENB":  "Enbridge",
        "MCD":  "McDonald's",
    },
    "Growth Stocks": {
        "AAPL":  "Apple",
        "MSFT":  "Microsoft",
        "NVDA":  "NVIDIA",
        "GOOGL": "Alphabet",
        "META":  "Meta Platforms",
        "AMZN":  "Amazon",
        "ASML":  "ASML Holding",
        "V":     "Visa",
        "UNH":   "UnitedHealth",
        "LLY":   "Eli Lilly",
    },
    "Macro Assets": {
        "GLD": "Gold ETF",
        "SLV": "Silver ETF",
        "TLT": "Long-term Treasuries",
        "SHY": "Short-term Treasuries",
        "XLE": "Energy Select SPDR",
        "XLU": "Utilities Select SPDR",
        "XLF": "Financials Select SPDR",
        "DBA": "Invesco Agriculture",
        "UUP": "USD Bull ETF",
        "EEM": "iShares MSCI EM",
    },
}

FRED_SERIES = {
    "Fed Funds Rate":   "FEDFUNDS",
    "Yield Curve 10-2": "T10Y2Y",
    "VIX":              "VIXCLS",
    "10Y Treasury":     "GS10",
    "US CPI":           "CPIAUCSL",
    "EUR/USD":          "DEXUSEU",
}

# ------------------------------------------------------------------ #
#  CSS — FULL BLACK THEME
# ------------------------------------------------------------------ #

st.markdown(f"""
<style>
  /* Global background and text */
  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stApp"], section.main {{
    background-color: {C['bg']} !important;
    color: {C['text']} !important;
  }}
  [data-testid="stSidebar"] {{
    background-color: #080808 !important;
    border-right: 1px solid {C['border']} !important;
  }}
  /* Headers */
  h1, h2, h3, h4, h5, h6, p, span, div, label {{
    color: {C['text']} !important;
  }}
  /* Tabs */
  [data-testid="stTabs"] button {{
    color: {C['muted']} !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
  }}
  [data-testid="stTabs"] button[aria-selected="true"] {{
    color: {C['blue']} !important;
    border-bottom: 2px solid {C['blue']} !important;
  }}
  /* Inputs */
  input, textarea, select {{
    background-color: #111111 !important;
    color: {C['text']} !important;
    border: 1px solid {C['border']} !important;
  }}
  /* Buttons */
  [data-testid="baseButton-primary"] {{
    background-color: {C['blue']} !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border: none !important;
  }}
  [data-testid="baseButton-secondary"] {{
    background-color: transparent !important;
    color: {C['text']} !important;
    border: 1px solid {C['border']} !important;
  }}
  /* Dataframe */
  [data-testid="stDataFrame"] {{
    background-color: {C['card']} !important;
  }}
  /* Expander */
  [data-testid="stExpander"] {{
    background-color: #0D0D0D !important;
    border: 1px solid {C['border']} !important;
    border-radius: 8px !important;
  }}
  /* Selectbox / multiselect */
  [data-testid="stSelectbox"] > div,
  [data-testid="stMultiSelect"] > div {{
    background-color: #111111 !important;
    color: {C['text']} !important;
  }}
  /* Divider */
  hr {{ border-color: {C['border']} !important; }}

  /* KPI cards */
  .kpi-box {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
  }}
  .kpi-label {{
    font-size: 11px; color: {C['muted']};
    text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px;
  }}
  .kpi-value {{ font-size: 24px; font-weight: 800; letter-spacing: -.01em; }}

  /* Section titles */
  .section-title {{
    font-size: 11px; font-weight: 600; color: {C['muted']};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 32px 0 14px;
    border-bottom: 1px solid {C['border']};
    padding-bottom: 8px;
  }}

  /* Login box */
  .login-box {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 40px 48px;
    max-width: 440px;
    margin: 80px auto;
    text-align: center;
  }}
  .login-title {{
    font-size: 26px; font-weight: 800; color: {C['text']};
    margin-bottom: 8px;
  }}
  .login-sub {{
    font-size: 13px; color: {C['muted']}; margin-bottom: 28px;
  }}
  .badge-admin {{
    display: inline-block;
    background: {C['green']}22;
    color: {C['green']};
    border: 1px solid {C['green']}55;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em;
  }}
  .badge-guest {{
    display: inline-block;
    background: {C['orange']}22;
    color: {C['orange']};
    border: 1px solid {C['orange']}55;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em;
  }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=C["bg"],
    plot_bgcolor=C["bg"],
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
    st.markdown(f'''<div class="kpi-box">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
    </div>''', unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  AUTHENTICATION
# ------------------------------------------------------------------ #

def generate_guest_password(length=10) -> str:
    """Genera password temporanea alfanumerica."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def get_admin_password() -> str:
    """Legge la password admin dai Streamlit Secrets."""
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except:
        return "admin123"  # fallback locale per testing

def check_auth() -> str | None:
    """
    Controlla lo stato di autenticazione.
    Restituisce: "admin", "guest", oppure None se non autenticato.
    """
    if "auth_role" not in st.session_state:
        return None
    if st.session_state["auth_role"] == "guest":
        # Verifica scadenza
        expiry = st.session_state.get("guest_expiry")
        if expiry and datetime.now() > expiry:
            st.session_state.pop("auth_role", None)
            st.session_state.pop("guest_expiry", None)
            return None
    return st.session_state["auth_role"]

def render_login():
    """Mostra la schermata di login."""
    st.markdown("""
    <div class="login-box">
        <div class="login-title">📈 Investment Dashboard</div>
        <div class="login-sub">Enter your password to access the dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        password = st.text_input("Password", type="password", key="login_pw",
                                  placeholder="Enter password...")
        if st.button("Access Dashboard", type="primary", use_container_width=True):
            admin_pw = get_admin_password()
            guest_pw = st.session_state.get("guest_password")
            guest_exp = st.session_state.get("guest_expiry")

            if password == admin_pw:
                st.session_state["auth_role"] = "admin"
                st.rerun()
            elif (guest_pw and password == guest_pw
                  and guest_exp and datetime.now() < guest_exp):
                st.session_state["auth_role"] = "guest"
                st.rerun()
            else:
                st.error("Wrong password or expired guest access.")

def render_auth_sidebar():
    """Mostra badge ruolo e logout nella sidebar."""
    role = st.session_state.get("auth_role", "")
    if role == "admin":
        st.sidebar.markdown('<span class="badge-admin">⚡ Admin</span>',
                            unsafe_allow_html=True)
        st.sidebar.markdown("---")

        # Genera password guest
        st.sidebar.markdown("**Guest Access**")
        if st.sidebar.button("🔑 Generate Guest Password"):
            pw  = generate_guest_password()
            exp = datetime.now() + timedelta(hours=GUEST_DURATION_HOURS)
            st.session_state["guest_password"] = pw
            st.session_state["guest_expiry"]   = exp
            st.sidebar.success(f"Password: `{pw}`")
            st.sidebar.caption(f"Expires: {exp.strftime('%H:%M')} "
                               f"({GUEST_DURATION_HOURS}h)")

        if st.session_state.get("guest_password"):
            exp = st.session_state.get("guest_expiry")
            remaining = (exp - datetime.now()).seconds // 60 if exp else 0
            if datetime.now() < exp:
                st.sidebar.info(f"Active guest pw: `{st.session_state['guest_password']}`\n\n"
                                f"Expires in {remaining} min")
            else:
                st.sidebar.caption("Guest password expired.")

        st.sidebar.markdown("---")
    else:
        st.sidebar.markdown('<span class="badge-guest">👁 Guest (read-only)</span>',
                            unsafe_allow_html=True)
        exp = st.session_state.get("guest_expiry")
        if exp:
            remaining = max(0, int((exp - datetime.now()).seconds / 60))
            st.sidebar.caption(f"Session expires in {remaining} min")
        st.sidebar.markdown("---")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("auth_role", None)
        st.rerun()

# ------------------------------------------------------------------ #
#  PERSISTENZA
# ------------------------------------------------------------------ #

def load_portfolio() -> dict:
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    default = {
        "VWCE.DE": {"ticker": "VWCE.DE", "quantity": 5.0,  "buy_price": 162.32, "currency": "EUR", "category": "UCITS Accumulo"},
        "EIMI.MI": {"ticker": "EIMI.MI", "quantity": 8.0,  "buy_price": 55.22,  "currency": "USD", "category": "UCITS Accumulo"},
        "DFNS.MI": {"ticker": "DFNS.MI", "quantity": 2.0,  "buy_price": 50.43,  "currency": "CHF", "category": "UCITS Accumulo"},
    }
    save_portfolio(default)
    return default

def save_portfolio(positions: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(positions, f, indent=2, default=str)

# ------------------------------------------------------------------ #
#  DATA FETCHING
# ------------------------------------------------------------------ #

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
        st.warning(f"Price download error: {e}")
    return result

@st.cache_data(ttl=7200)
def fetch_fx_rates() -> dict:
    pairs = {"USD": "EURUSD=X", "CHF": "EURCHF=X", "GBP": "EURGBP=X"}
    rates = {"EUR": 1.0}
    for currency, pair in pairs.items():
        try:
            data = yf.download(pair, period="2d", progress=False, auto_adjust=True)
            if not data.empty:
                rates[currency] = 1 / float(data["Close"].iloc[-1])
        except:
            pass
    return rates

@st.cache_data(ttl=86400)
def fetch_macro() -> pd.DataFrame:
    frames = {}
    for name, sid in FRED_SERIES.items():
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            df = pd.read_csv(url, index_col=0, parse_dates=True, na_values=".")
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
    for ticker in tickers:
        try:
            result[ticker] = yf.Ticker(ticker).dividends
            time.sleep(0.2)
        except:
            result[ticker] = pd.Series(dtype=float)
    return result

# ------------------------------------------------------------------ #
#  SCORING
# ------------------------------------------------------------------ #

def rank_norm(s: pd.Series, asc: bool = True) -> pd.Series:
    if s.isna().all():
        return pd.Series(0.5, index=s.index)
    r = s.rank(ascending=asc, na_option="bottom")
    return (r - 1) / max(r.max() - 1, 1)

def score_etf(prices: pd.DataFrame, names: dict) -> pd.DataFrame:
    rows = []
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 60:
            continue
        ret = s.pct_change().dropna()
        m12 = (s.iloc[-1]/s.iloc[max(0,len(s)-252)]-1) if len(s)>252 else np.nan
        m6  = (s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        m3  = (s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1)  if len(s)>63  else np.nan
        r1y = ret.iloc[-252:] if len(ret)>=252 else ret
        vol = r1y.std()*np.sqrt(252)
        sh  = (r1y.mean()*252)/vol if vol>0 else np.nan
        rows.append({"Ticker": ticker, "Name": names.get(ticker, ticker),
                     "Return 12M": m12, "Return 6M": m6, "Return 3M": m3,
                     "Annual Vol": vol, "Sharpe 1Y": sh})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty:
        return df
    df["Score"] = (0.30*rank_norm(df["Return 12M"]) + 0.20*rank_norm(df["Return 6M"]) +
                   0.15*rank_norm(df["Return 3M"])   + 0.15*rank_norm(df["Annual Vol"], False) +
                   0.20*rank_norm(df["Sharpe 1Y"]))
    return df.sort_values("Score", ascending=False)

def score_dividend(prices, names, fundamentals, dividends) -> pd.DataFrame:
    rows = []
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 60 or ticker not in fundamentals.index:
            continue
        f = fundamentals.loc[ticker]
        divs = dividends.get(ticker, pd.Series(dtype=float))
        div_growth, div_years = np.nan, 0
        if divs is not None and len(divs) > 1:
            try:
                ann = divs.resample("YE").sum()
                ann = ann[ann > 0]
                if len(ann) >= 2:
                    n = min(5, len(ann)-1)
                    div_growth = (ann.iloc[-1]/ann.iloc[-(n+1)])**(1/n) - 1
                div_years = sum(1 for v in reversed(ann.values) if v > 0)
            except:
                pass
        fcf_yield = np.nan
        if pd.notna(f.get("FCF")) and pd.notna(f.get("Market Cap")) and f["Market Cap"] > 0:
            fcf_yield = f["FCF"] / f["Market Cap"]
        rows.append({"Ticker": ticker, "Name": names.get(ticker, str(f.get("Name", ticker))),
                     "Dividend Yield": f.get("Dividend Yield"), "Payout Ratio": f.get("Payout Ratio"),
                     "Div Growth 5Y": div_growth, "Consec. Years": div_years,
                     "FCF Yield": fcf_yield, "Debt/Equity": f.get("Debt/Equity")})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty:
        return df
    df["Score"] = (0.25*rank_norm(df["Dividend Yield"])      + 0.20*rank_norm(df["Payout Ratio"], False) +
                   0.20*rank_norm(df["Div Growth 5Y"])        + 0.15*rank_norm(df["Consec. Years"]) +
                   0.10*rank_norm(df["FCF Yield"])            + 0.10*rank_norm(df["Debt/Equity"], False))
    return df.sort_values("Score", ascending=False)

def score_growth(prices, names, fundamentals) -> pd.DataFrame:
    rows = []
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 60 or ticker not in fundamentals.index:
            continue
        f  = fundamentals.loc[ticker]
        m6 = (s.iloc[-1]/s.iloc[max(0,len(s)-126)]-1) if len(s)>126 else np.nan
        ups = np.nan
        if pd.notna(f.get("Analyst Target")) and s.iloc[-1] > 0:
            ups = (f["Analyst Target"] - s.iloc[-1]) / s.iloc[-1]
        rows.append({"Ticker": ticker, "Name": names.get(ticker, str(f.get("Name", ticker))),
                     "Revenue Growth": f.get("Revenue Growth"), "EPS Growth": f.get("EPS Growth"),
                     "ROE": f.get("ROE"), "Profit Margin": f.get("Profit Margin"),
                     "Momentum 6M": m6, "Analyst Upside": ups, "Forward P/E": f.get("Forward P/E")})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty:
        return df
    df["Score"] = (0.25*rank_norm(df["Revenue Growth"]) + 0.20*rank_norm(df["EPS Growth"]) +
                   0.20*rank_norm(df["ROE"])             + 0.15*rank_norm(df["Profit Margin"]) +
                   0.10*rank_norm(df["Momentum 6M"])     + 0.10*rank_norm(df["Analyst Upside"]))
    return df.sort_values("Score", ascending=False)

def score_macro(prices, names) -> pd.DataFrame:
    rows = []
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 30:
            continue
        ret = s.pct_change().dropna()
        m3  = (s.iloc[-1]/s.iloc[max(0,len(s)-63)]-1)  if len(s)>63  else np.nan
        m1  = (s.iloc[-1]/s.iloc[max(0,len(s)-21)]-1)  if len(s)>21  else np.nan
        r6  = ret.iloc[-126:] if len(ret)>=126 else ret
        vol = ret.iloc[-63:].std()*np.sqrt(252) if len(ret)>=63 else ret.std()*np.sqrt(252)
        sh  = (r6.mean()*252)/(r6.std()*np.sqrt(252)) if r6.std()>0 else np.nan
        rows.append({"Ticker": ticker, "Name": names.get(ticker, ticker),
                     "Momentum 3M": m3, "Momentum 1M": m1,
                     "Sharpe 6M": sh, "Volatility 3M": vol})
    df = pd.DataFrame(rows).set_index("Ticker")
    if df.empty:
        return df
    df["Score"] = (0.35*rank_norm(df["Momentum 3M"])    + 0.25*rank_norm(df["Momentum 1M"]) +
                   0.25*rank_norm(df["Sharpe 6M"])       + 0.15*rank_norm(df["Volatility 3M"], False))
    return df.sort_values("Score", ascending=False)

# ------------------------------------------------------------------ #
#  PORTFOLIO & RISK
# ------------------------------------------------------------------ #

def calc_portfolio(positions, current_prices, fx_rates):
    rows = []
    total_value = 0.0
    for ticker, pos in positions.items():
        qty      = float(pos["quantity"])
        buy_px   = float(pos["buy_price"])
        currency = pos.get("currency", "EUR")
        fx       = fx_rates.get(currency, 1.0)
        curr_px  = current_prices.get(ticker)
        cost_eur = qty * buy_px * fx
        val_eur  = qty * curr_px * fx if curr_px else None
        pl_eur   = (val_eur - cost_eur) if val_eur else None
        pl_pct   = (pl_eur / cost_eur) if (pl_eur is not None and cost_eur > 0) else None
        total_value += val_eur or cost_eur
        rows.append({"Ticker": ticker, "Category": pos.get("category",""),
                     "Qty": qty, "Buy Price": buy_px, "Currency": currency,
                     "Current Price": curr_px, "Cost (€)": round(cost_eur,2),
                     "Value (€)": round(val_eur,2) if val_eur else None,
                     "P&L (€)": round(pl_eur,2) if pl_eur is not None else None,
                     "P&L (%)": pl_pct})
    df = pd.DataFrame(rows).set_index("Ticker")
    df["Weight"] = df["Value (€)"] / total_value if total_value > 0 else 0
    return df, total_value

def calc_risk(port_ret, total_value, confidence=0.95, horizon=1):
    q       = 1 - confidence
    var_h   = -np.percentile(port_ret, q*100) * np.sqrt(horizon)
    tail    = port_ret[port_ret <= np.percentile(port_ret, q*100)]
    cvar_h  = -tail.mean() * np.sqrt(horizon) if len(tail) > 0 else var_h
    mu, sig = port_ret.mean(), port_ret.std()
    z       = stats.norm.ppf(q)
    var_p   = -(mu*horizon + z*sig*np.sqrt(horizon))
    ann_ret = (1+port_ret).prod()**(252/len(port_ret)) - 1
    vol     = sig * np.sqrt(252)
    sharpe  = ann_ret / vol if vol > 0 else np.nan
    down    = port_ret[port_ret < 0]
    sortino = ann_ret / (down.std()*np.sqrt(252)) if len(down) > 0 else np.nan
    cum     = (1+port_ret).cumprod()
    dd      = (cum - cum.expanding().max()) / cum.expanding().max()
    return {"annual_return": ann_ret, "volatility": vol, "sharpe": sharpe,
            "sortino": sortino, "max_drawdown": dd.min(),
            "hit_rate": (port_ret>0).mean(),
            "var_hist_pct": var_h, "var_hist_eur": var_h*total_value,
            "cvar_hist_eur": cvar_h*total_value,
            "var_para_pct": var_p, "var_para_eur": var_p*total_value,
            "drawdown_series": dd, "cumulative_returns": cum}

# ------------------------------------------------------------------ #
#  SIDEBAR
# ------------------------------------------------------------------ #

def render_sidebar(positions, is_admin):
    st.sidebar.title("📂 Portfolio Manager")
    render_auth_sidebar()

    if not is_admin:
        st.sidebar.caption("👁 Read-only mode. Contact admin to modify positions.")
        return positions

    budget = st.sidebar.number_input(
        "Monthly Budget (€)", min_value=0.0,
        value=float(st.session_state.get("budget", BUDGET_DEFAULT)),
        step=50.0, format="%.0f", key="budget_input"
    )
    st.session_state["budget"] = budget

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current Positions**")

    updated = dict(positions)
    for ticker in list(updated.keys()):
        with st.sidebar.expander(f"✏️ {ticker}"):
            pos     = updated[ticker]
            new_qty = st.number_input("Quantity", min_value=0.0, value=float(pos["quantity"]),
                                      step=0.5, key=f"qty_{ticker}")
            new_px  = st.number_input("Avg Buy Price", min_value=0.0, value=float(pos["buy_price"]),
                                      step=0.01, key=f"px_{ticker}", format="%.4f")
            new_cat = st.text_input("Category", value=pos.get("category",""), key=f"cat_{ticker}")
            new_cur = st.selectbox("Currency", ["EUR","USD","CHF","GBP"],
                                   index=["EUR","USD","CHF","GBP"].index(pos.get("currency","EUR")),
                                   key=f"cur_{ticker}")
            if st.button("🗑 Remove", key=f"del_{ticker}"):
                del updated[ticker]
                save_portfolio(updated)
                st.rerun()
            else:
                updated[ticker] = {**pos, "quantity": new_qty, "buy_price": new_px,
                                   "category": new_cat, "currency": new_cur}

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Add New Position**")
    new_t   = st.sidebar.text_input("Ticker", placeholder="e.g. AAPL, VWCE.DE").upper().strip()
    new_qty = st.sidebar.number_input("Quantity",  min_value=0.01, value=1.0,  step=0.5,  key="nqty")
    new_px  = st.sidebar.number_input("Buy Price", min_value=0.01, value=10.0, step=0.01, key="npx", format="%.4f")
    new_cur = st.sidebar.selectbox("Currency", ["EUR","USD","CHF","GBP"], key="ncur")
    new_cat = st.sidebar.text_input("Category", placeholder="e.g. UCITS Accumulo", key="ncat")

    if st.sidebar.button("➕ Add Position", type="primary"):
        if new_t:
            updated[new_t] = {"ticker": new_t, "quantity": new_qty, "buy_price": new_px,
                               "currency": new_cur, "category": new_cat, "notes": ""}
            save_portfolio(updated)
            st.rerun()
        else:
            st.sidebar.error("Enter a valid ticker.")

    if st.sidebar.button("💾 Save Changes"):
        save_portfolio(updated)
        st.sidebar.success("Saved!")

    return updated

# ------------------------------------------------------------------ #
#  SCORE BAR CHART
# ------------------------------------------------------------------ #

def render_score_chart(df, title, color):
    if df.empty or "Score" not in df.columns:
        st.info("No data available.")
        return
    df2    = df[["Score"]].sort_values("Score", ascending=True)
    name_c = "Name" if "Name" in df.columns else None
    labels = [f"{t} — {df.loc[t,'Name'][:25]}" if name_c else t for t in df2.index]
    fig = go.Figure(go.Bar(
        y=labels, x=df2["Score"].values, orientation="h",
        marker=dict(color=df2["Score"].values, colorscale=[
            [0, C["border"]], [0.5, color+"88"], [1, color]
        ], showscale=False),
        text=[f"{v:.2f}" for v in df2["Score"].values],
        textposition="outside", textfont=dict(color=C["text"]),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>"
    ))
    fig.add_vline(x=0.5, line_color=C["muted"], line_dash="dash",
                  annotation_text="0.5", annotation_font_color=C["muted"])
    fig.update_xaxes(range=[0, 1.2])
    apply_layout(fig, title, 420)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #

def main():
    # Auth check
    role = check_auth()
    if role is None:
        render_login()
        return

    is_admin = role == "admin"

    # Session init
    if "positions" not in st.session_state:
        st.session_state["positions"] = load_portfolio()
    if "budget" not in st.session_state:
        st.session_state["budget"] = BUDGET_DEFAULT

    positions = render_sidebar(st.session_state["positions"], is_admin)
    if is_admin:
        st.session_state["positions"] = positions

    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("📈 Investment Dashboard")
        st.caption(f"Last updated: {datetime.now().strftime('%d %B %Y, %H:%M')}")
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Prices", type="primary"):
                st.cache_data.clear()
                st.rerun()
        with c2:
            if st.button("🔄 All"):
                st.cache_data.clear()
                st.rerun()

    if not positions:
        st.info("No positions. Add assets from the sidebar.")
        return

    # Data
    tickers_ptf    = tuple(sorted(positions.keys()))
    current_prices = fetch_current_prices(tickers_ptf)
    fx_rates       = fetch_fx_rates()

    pivot, total_value = calc_portfolio(positions, current_prices, fx_rates)
    total_cost = pd.to_numeric(pivot["Cost (€)"], errors="coerce").sum()
    total_pl   = pd.to_numeric(pivot["P&L (€)"],  errors="coerce").sum()
    budget     = st.session_state["budget"]

    # ================================================================
    #  TABS
    # ================================================================
    tab_ptf, tab_risk, tab_screen, tab_macro = st.tabs([
        "💼 Portfolio", "⚠️ Risk & VaR", "🔍 Screening", "🌍 Macro"
    ])

    # ================================================================
    #  TAB 1 — PORTFOLIO
    # ================================================================
    with tab_ptf:
        section("Overview")
        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi("Total Value", f"€{total_value:,.0f}", C["blue"])
        with k2:
            pl_color = C["green"] if total_pl >= 0 else C["red"]
            kpi("Unrealised P&L",
                f"€{total_pl:+,.0f} ({total_pl/total_cost:+.1%})" if total_cost>0 else "N/A",
                pl_color)
        with k3: kpi("Positions", str(len(positions)), C["teal"])
        with k4: kpi("Monthly Budget", f"€{budget:,.0f}", C["purple"])

        section("Positions")
        disp = pivot.copy()
        disp["Buy Price"]     = disp.apply(lambda r: f"{r['Buy Price']:.2f} {r['Currency']}", axis=1)
        disp["Current Price"] = disp.apply(
            lambda r: f"{r['Current Price']:.2f} {r['Currency']}" if pd.notna(r["Current Price"]) else "N/A", axis=1)
        disp["Cost (€)"]  = disp["Cost (€)"].map("€{:,.2f}".format)
        disp["Value (€)"] = disp["Value (€)"].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
        disp["P&L (€)"]   = disp["P&L (€)"].apply(lambda x: f"€{x:+,.2f}" if pd.notna(x) else "N/A")
        disp["P&L (%)"]   = disp["P&L (%)"].apply(lambda x: f"{x:+.2%}" if pd.notna(x) else "N/A")
        disp["Weight"]    = disp["Weight"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        st.dataframe(disp[["Category","Qty","Buy Price","Current Price",
                             "Cost (€)","Value (€)","P&L (€)","P&L (%)","Weight"]],
                     use_container_width=True)

        section("Allocation & Monthly Budget")
        col_pie, col_alloc = st.columns(2)

        with col_pie:
            vals = pd.to_numeric(pivot["Value (€)"], errors="coerce").fillna(0)
            fig_pie = go.Figure(go.Pie(
                labels=pivot.index.tolist(), values=vals.tolist(), hole=0.45,
                textinfo="label+percent", textfont=dict(color=C["text"]),
                marker=dict(colors=CHART_COLORS),
                hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>"
            ))
            fig_pie.add_annotation(text=f"€{total_value:,.0f}", x=0.5, y=0.5,
                font=dict(size=16, color=C["text"], family="Inter"), showarrow=False)
            apply_layout(fig_pie, "Portfolio Allocation", 360)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_alloc:
            section("Budget Split")
            alloc_rows = []
            for ticker, row in pivot.iterrows():
                w        = float(row["Weight"]) if isinstance(row["Weight"], float) else 0
                bud_eur  = budget * w
                curr_px  = current_prices.get(ticker)
                currency = positions[ticker].get("currency","EUR")
                price_eur= curr_px * fx_rates.get(currency,1.0) if curr_px else None
                qty_sug  = bud_eur / price_eur if price_eur else None
                alloc_rows.append({
                    "Ticker":       ticker,
                    "Weight":       f"{w:.1%}",
                    "Budget (€)":   f"€{bud_eur:.2f}",
                    "Price (€)":    f"€{price_eur:.2f}" if price_eur else "N/A",
                    "Units to buy": f"{qty_sug:.3f}" if qty_sug else "N/A",
                })
            alloc_df = pd.DataFrame(alloc_rows)
            alloc_df.loc[len(alloc_df)] = ["TOTAL","100%",f"€{budget:.2f}","",""]
            st.dataframe(alloc_df.set_index("Ticker"), use_container_width=True)

        pl_vals = pd.to_numeric(pivot["P&L (€)"], errors="coerce")
        pl_cols = [C["green"] if v >= 0 else C["red"] for v in pl_vals]
        fig_pl  = go.Figure(go.Bar(
            x=pivot.index.tolist(), y=pl_vals.tolist(), marker_color=pl_cols,
            text=[f"€{v:+,.0f}" for v in pl_vals], textposition="outside",
            textfont=dict(color=C["text"]),
            hovertemplate="<b>%{x}</b><br>P&L: €%{y:+,.2f}<extra></extra>"
        ))
        fig_pl.add_hline(y=0, line_color=C["muted"], line_width=1)
        apply_layout(fig_pl, f"Unrealised P&L  |  Total: €{total_pl:+,.0f}", 340)
        st.plotly_chart(fig_pl, use_container_width=True)

    # ================================================================
    #  TAB 2 — RISK
    # ================================================================
    with tab_risk:
        prices_ptf = fetch_prices(tickers_ptf, "3y")
        valid_t    = [t for t in tickers_ptf if t in prices_ptf.columns]

        if len(valid_t) < 1:
            st.warning("Not enough price history.")
        else:
            w_raw  = {t: float(pivot.loc[t,"Value (€)"]) for t in valid_t
                      if t in pivot.index and pd.notna(pivot.loc[t,"Value (€)"])}
            w_tot  = sum(w_raw.values())
            w_norm = {t: v/w_tot for t,v in w_raw.items()} if w_tot > 0 else {}

            if w_norm:
                w_arr    = np.array([w_norm[t] for t in valid_t if t in w_norm])
                ret_df   = prices_ptf[[t for t in valid_t if t in w_norm]].pct_change().dropna()
                port_ret = (ret_df * w_arr).sum(axis=1)

                r95   = calc_risk(port_ret, total_value, 0.95, 1)
                r99   = calc_risk(port_ret, total_value, 0.99, 1)
                r95_5 = calc_risk(port_ret, total_value, 0.95, 5)

                section("Performance")
                m1,m2,m3,m4 = st.columns(4)
                with m1: kpi("Annual Return", f"{r95['annual_return']:+.1%}",
                              C["green"] if r95["annual_return"]>=0 else C["red"])
                with m2: kpi("Sharpe Ratio",     f"{r95['sharpe']:.2f}",       C["teal"])
                with m3: kpi("Max Drawdown",      f"{r95['max_drawdown']:.1%}", C["red"])
                with m4: kpi("Annual Volatility", f"{r95['volatility']:.1%}",   C["orange"])

                section("Value at Risk")
                v1,v2,v3 = st.columns(3)
                with v1: kpi("VaR 95% — 1 day",
                              f"€{r95['var_hist_eur']:,.0f} ({r95['var_hist_pct']:.2%})", C["orange"])
                with v2: kpi("VaR 99% — 1 day",
                              f"€{r99['var_hist_eur']:,.0f} ({r99['var_hist_pct']:.2%})", C["red"])
                with v3: kpi("VaR 95% — 5 days",
                              f"€{r95_5['var_hist_eur']:,.0f} ({r95_5['var_hist_pct']:.2%})", C["yellow"])

                cum_r = r95["cumulative_returns"]
                dd    = r95["drawdown_series"]
                fig_p = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                      row_heights=[0.65,0.35], vertical_spacing=0.04)
                fig_p.add_trace(go.Scatter(
                    x=cum_r.index, y=(cum_r-1)*100, name="Cumulative Return %",
                    fill="tozeroy", fillcolor=C["blue"]+"22",
                    line=dict(color=C["blue"], width=2),
                    hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"
                ), row=1, col=1)
                fig_p.add_trace(go.Scatter(
                    x=dd.index, y=dd.values*100, name="Drawdown %",
                    fill="tozeroy", fillcolor=C["red"]+"33",
                    line=dict(color=C["red"], width=1.5),
                    hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"
                ), row=2, col=1)
                fig_p.update_layout(**PLOTLY_LAYOUT, height=440,
                    title=dict(text="Cumulative Return & Drawdown",
                               font=dict(size=13,color=C["text"])))
                fig_p.update_xaxes(gridcolor=C["border"])
                fig_p.update_yaxes(gridcolor=C["border"])
                st.plotly_chart(fig_p, use_container_width=True)

                col_d, col_c = st.columns(2)
                with col_d:
                    fig_dist = go.Figure()
                    fig_dist.add_trace(go.Histogram(
                        x=port_ret.values*100, nbinsx=60,
                        marker_color=C["purple"], opacity=0.85
                    ))
                    fig_dist.add_vline(x=-r95["var_hist_pct"]*100,
                        line_color=C["orange"], line_width=2, line_dash="dash",
                        annotation_text=f"VaR 95%",
                        annotation_font_color=C["orange"])
                    fig_dist.add_vline(x=-r99["var_hist_pct"]*100,
                        line_color=C["red"], line_width=2, line_dash="dash",
                        annotation_text=f"VaR 99%",
                        annotation_font_color=C["red"])
                    apply_layout(fig_dist, "Return Distribution + VaR", 380)
                    st.plotly_chart(fig_dist, use_container_width=True)

                with col_c:
                    corr = ret_df.corr()
                    fig_corr = go.Figure(go.Heatmap(
                        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                        colorscale=[[0,C["red"]],[0.5,"#111111"],[1,C["green"]]],
                        zmin=-1, zmax=1,
                        text=[[f"{v:.2f}" for v in row] for row in corr.values],
                        texttemplate="%{text}", textfont=dict(color=C["text"]),
                        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>"
                    ))
                    apply_layout(fig_corr, "Correlation Matrix", 380)
                    st.plotly_chart(fig_corr, use_container_width=True)

    # ================================================================
    #  TAB 3 — SCREENING
    # ================================================================
    with tab_screen:
        section("Asset Screening — Composite Scores (0 = worst, 1 = best in group)")
        st.caption("Cache: 1 hour. Click 'Refresh All' to force update.")

        cat_colors = {
            "UCITS Accumulation": C["blue"],
            "ETF Accumulation":   C["green"],
            "Dividend Stocks":    C["orange"],
            "Growth Stocks":      C["purple"],
            "Macro Assets":       C["teal"],
        }

        selected_cat = st.selectbox("Select category", list(UNIVERSE.keys()))
        color        = cat_colors[selected_cat]
        names        = UNIVERSE[selected_cat]
        tickers_cat  = tuple(sorted(names.keys()))

        with st.spinner(f"Loading {selected_cat}..."):
            prices_cat = fetch_prices(tickers_cat, "3y")
            valid_cat  = [t for t in tickers_cat if t in prices_cat.columns]

            if selected_cat in ["UCITS Accumulation","ETF Accumulation"]:
                scores = score_etf(prices_cat[valid_cat], names)
            elif selected_cat == "Dividend Stocks":
                fund = fetch_fundamentals(tickers_cat)
                divs = fetch_dividends(tickers_cat)
                scores = score_dividend(prices_cat[valid_cat], names, fund, divs)
            elif selected_cat == "Growth Stocks":
                fund = fetch_fundamentals(tickers_cat)
                scores = score_growth(prices_cat[valid_cat], names, fund)
            else:
                scores = score_macro(prices_cat[valid_cat], names)

        if not scores.empty:
            render_score_chart(scores, f"Composite Score — {selected_cat}", color)
            section("Full Data Table")
            fmt = scores.copy()
            for col in fmt.columns:
                if col == "Name":
                    continue
                elif col == "Score":
                    fmt[col] = fmt[col].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
                elif any(k in col for k in ["Return","Growth","Yield","Margin","ROE","Vol","Momentum"]):
                    fmt[col] = fmt[col].map(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
                else:
                    fmt[col] = fmt[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            st.dataframe(fmt, use_container_width=True)
        else:
            st.warning("No data for this category.")

    # ================================================================
    #  TAB 4 — MACRO
    # ================================================================
    with tab_macro:
        section("Macroeconomic Context (FRED)")
        macro = fetch_macro()

        if not macro.empty:
            latest = macro.ffill().iloc[-1]
            mk1,mk2,mk3,mk4 = st.columns(4)
            with mk1: kpi("Fed Funds Rate",
                           f"{latest.get('Fed Funds Rate', float('nan')):.2f}%", C["blue"])
            with mk2:
                yc = latest.get("Yield Curve 10-2", float("nan"))
                kpi("Yield Curve 10Y-2Y",
                    f"{yc:.2f}%  {'⚠️ Inverted' if yc<0 else '✅ Normal'}",
                    C["red"] if yc<0 else C["green"])
            with mk3: kpi("VIX", f"{latest.get('VIX', float('nan')):.1f}", C["orange"])
            with mk4: kpi("10Y Treasury",
                           f"{latest.get('10Y Treasury', float('nan')):.2f}%", C["teal"])

            selected_macro = st.multiselect(
                "Select indicators",
                options=macro.columns.tolist(),
                default=macro.columns.tolist()
            )
            if selected_macro:
                cols_m = st.columns(2)
                for i, col_name in enumerate(selected_macro):
                    with cols_m[i % 2]:
                        s = macro[col_name].dropna().iloc[-10*12:]
                        color_m = CHART_COLORS[i % len(CHART_COLORS)]
                        r,g,b = (int(color_m[j:j+2],16) for j in (1,3,5))
                        fig = go.Figure(go.Scatter(
                            x=s.index, y=s.values, fill="tozeroy",
                            fillcolor=f"rgba({r},{g},{b},0.15)",
                            line=dict(color=color_m, width=2),
                            hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"
                        ))
                        fig.add_annotation(
                            text=f"  {s.iloc[-1]:.2f}", x=s.index[-1], y=s.iloc[-1],
                            font=dict(size=12, color=color_m, family="Inter"),
                            showarrow=False)
                        apply_layout(fig, col_name, 280)
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Macro data unavailable.")

    st.markdown("---")
    st.caption("Data: Yahoo Finance · FRED  |  ~15min delayed  |  Not financial advice.")

if __name__ == "__main__":
    main()

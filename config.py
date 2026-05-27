"""
config.py — Costanti globali, universo asset, colori, ISIN map.
"""
from pathlib import Path

# ------------------------------------------------------------------ #
#  FILE PATHS
# ------------------------------------------------------------------ #
PORTFOLIO_CACHE  = Path("last_portfolio.json")
BUY_PRICES_FILE  = Path("buy_prices.json")
GUEST_PW_FILE    = Path("guest_pw.json")
COMMISSIONS_FILE = Path("commissions.json")
SNAPSHOTS_FILE   = Path("snapshots.json")

# ------------------------------------------------------------------ #
#  APP SETTINGS
# ------------------------------------------------------------------ #
BUDGET_DEFAULT   = 1300.0
GUEST_HOURS      = 1

# ------------------------------------------------------------------ #
#  COLORS
# ------------------------------------------------------------------ #
C = {
    "blue":   "#00B4FF", "green":  "#00FF94", "red":    "#FF3B3B",
    "orange": "#FF9500", "purple": "#BF5FFF", "teal":   "#00FFD1",
    "yellow": "#FFE600", "pink":   "#FF2D9B", "muted":  "#6B7280",
    "bg":     "#000000", "card":   "#0D0D0D", "border": "#1F1F1F",
    "text":   "#FFFFFF",
}
CHART_COLORS = [
    "#00B4FF","#00FF94","#FF9500","#BF5FFF",
    "#FF3B3B","#00FFD1","#FFE600","#FF2D9B",
]

# ------------------------------------------------------------------ #
#  ISIN → YAHOO TICKER MAP
# ------------------------------------------------------------------ #
ISIN_MAP = {
    "IE00BKM4GZ66": {"ticker": "EIMI.L",  "currency": "USD", "name": "iShares Core MSCI EM IMI"},
    "IE000YYE6WK5": {"ticker": "DFNS.SW", "currency": "CHF", "name": "VanEck Defense ETF"},
    "IE00BK5BQT80": {"ticker": "VWCE.DE", "currency": "EUR", "name": "Vanguard FTSE All-World"},
    "IE00B4L5Y983": {"ticker": "IWDA.AS", "currency": "USD", "name": "iShares Core MSCI World"},
    "IE0031442068": {"ticker": "CSPX.L",  "currency": "USD", "name": "iShares Core S&P 500"},
    "IE00B52MJY50": {"ticker": "VUSA.AS", "currency": "USD", "name": "Vanguard S&P 500"},
    "IE00B3XXRP09": {"ticker": "VWRL.AS", "currency": "USD", "name": "Vanguard FTSE All-World Dist"},
}

# ------------------------------------------------------------------ #
#  UNIVERSE
# ------------------------------------------------------------------ #
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
        "JNJ": "Johnson & Johnson", "PG":  "Procter & Gamble",
        "KO":  "Coca-Cola",         "ABBV":"AbbVie",
        "MO":  "Altria Group",      "T":   "AT&T",
        "VZ":  "Verizon",           "O":   "Realty Income",
        "ENB": "Enbridge",          "MCD": "McDonald's",
    },
    "Growth Stocks": {
        "AAPL": "Apple",       "MSFT": "Microsoft",   "NVDA": "NVIDIA",
        "GOOGL":"Alphabet",    "META": "Meta",        "AMZN": "Amazon",
        "ASML": "ASML Holding","V":    "Visa",        "UNH":  "UnitedHealth",
        "LLY":  "Eli Lilly",
    },
    "Macro Assets": {
        "GLD": "Gold ETF",          "SLV": "Silver ETF",
        "TLT": "Long-term Treasury","SHY": "Short-term Treasury",
        "XLE": "Energy SPDR",       "XLU": "Utilities SPDR",
        "XLF": "Financials SPDR",   "DBA": "Invesco Agriculture",
        "UUP": "USD Bull ETF",      "EEM": "iShares MSCI EM",
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
#  PLOTLY LAYOUT
# ------------------------------------------------------------------ #
PLOTLY_LAYOUT = dict(
    paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
    font=dict(color=C["text"], family="Inter, system-ui, sans-serif", size=12),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"]),
)

# ------------------------------------------------------------------ #
#  CSS
# ------------------------------------------------------------------ #
CSS = f"""
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
  [data-testid="stFileUploader"] {{
    background-color: #0D0D0D !important; border: 1px dashed #444 !important;
    border-radius: 10px !important;
  }}
  .stCaption, small {{ color: {C['muted']} !important; }}
  [data-testid="stAlert"] {{
    background-color: #111 !important; border: 1px solid #333 !important;
    color: {C['text']} !important;
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
"""

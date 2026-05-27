"""
config.py — Costanti globali, universo asset, colori, ISIN map, CSS.
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
WATCHLIST_FILE   = Path("watchlist.json")

# ------------------------------------------------------------------ #
#  SETTINGS
# ------------------------------------------------------------------ #
BUDGET_DEFAULT = 1300.0
GUEST_HOURS    = 1

# Trusted news sources whitelist
TRUSTED_SOURCES = {
    "reuters":       "Reuters",
    "ft.com":        "Financial Times",
    "bloomberg":     "Bloomberg",
    "cnbc":          "CNBC",
    "wsj":           "Wall Street Journal",
    "marketwatch":   "MarketWatch",
    "seekingalpha":  "Seeking Alpha",
    "morningstar":   "Morningstar",
    "barrons":       "Barron's",
    "economist":     "The Economist",
}

# ------------------------------------------------------------------ #
#  COLORS
# ------------------------------------------------------------------ #
C = {
    "blue":    "#00B4FF", "green":   "#00FF94", "red":     "#FF3B3B",
    "orange":  "#FF9500", "purple":  "#BF5FFF", "teal":    "#00FFD1",
    "yellow":  "#FFE600", "pink":    "#FF2D9B", "muted":   "#6B7280",
    "bg":      "#000000", "card":    "#0D0D0D", "border":  "#1F1F1F",
    "card2":   "#111111", "text":    "#FFFFFF", "subtext": "#A0AEC0",
}
CHART_COLORS = [
    "#00B4FF","#00FF94","#FF9500","#BF5FFF",
    "#FF3B3B","#00FFD1","#FFE600","#FF2D9B",
]

# Rank colors for screening
RANK_COLORS = {
    "high":   "#00FF94",  # top tercile
    "mid":    "#FFE600",  # middle
    "low":    "#FF3B3B",  # bottom
}

# ------------------------------------------------------------------ #
#  ISIN MAP
# ------------------------------------------------------------------ #
ISIN_MAP = {
    "IE00BKM4GZ66": {"ticker": "EIMI.L",  "currency": "USD", "name": "iShares Core MSCI EM IMI",     "accumulation": True},
    "IE000YYE6WK5": {"ticker": "DFNS.SW", "currency": "CHF", "name": "VanEck Defense ETF",           "accumulation": True},
    "IE00BK5BQT80": {"ticker": "VWCE.DE", "currency": "EUR", "name": "Vanguard FTSE All-World Acc",  "accumulation": True},
    "IE00B4L5Y983": {"ticker": "IWDA.AS", "currency": "USD", "name": "iShares Core MSCI World Acc",  "accumulation": True},
    "IE0031442068": {"ticker": "CSPX.L",  "currency": "USD", "name": "iShares Core S&P 500 Acc",     "accumulation": True},
    "IE00B52MJY50": {"ticker": "VUSA.AS", "currency": "USD", "name": "Vanguard S&P 500 Acc",         "accumulation": True},
    "IE00B3XXRP09": {"ticker": "VWRL.AS", "currency": "USD", "name": "Vanguard FTSE All-World Dist", "accumulation": False},
    "IE00B3RBWM25": {"ticker": "VWRD.AS", "currency": "USD", "name": "Vanguard FTSE All-World Dist", "accumulation": False},
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
        "AAPL":"Apple",    "MSFT":"Microsoft", "NVDA":"NVIDIA",
        "GOOGL":"Alphabet","META":"Meta",       "AMZN":"Amazon",
        "ASML":"ASML",     "V":  "Visa",        "UNH":"UnitedHealth",
        "LLY": "Eli Lilly",
    },
    "Macro Assets": {
        "GLD":"Gold ETF",          "SLV":"Silver ETF",
        "TLT":"Long-term Treasury","SHY":"Short-term Treasury",
        "XLE":"Energy SPDR",       "XLU":"Utilities SPDR",
        "XLF":"Financials SPDR",   "DBA":"Invesco Agriculture",
        "UUP":"USD Bull ETF",      "EEM":"iShares MSCI EM",
    },
}

FRED_SERIES = {
    "Fed Funds Rate":   "FEDFUNDS",
    "Yield Curve 10-2": "T10Y2Y",
    "VIX":              "VIXCLS",
    "10Y Treasury":     "GS10",
    "2Y Treasury":      "GS2",
    "US CPI":           "CPIAUCSL",
    "EUR/USD":          "DEXUSEU",
    "US Unemployment":  "UNRATE",
    "M2 Money Supply":  "M2SL",
}

# ------------------------------------------------------------------ #
#  PLOTLY BASE LAYOUT
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
    background-color: #060606 !important;
    border-right: 1px solid {C['border']} !important;
  }}
  h1,h2,h3,h4,h5,h6,p,label,.stMarkdown {{ color: {C['text']} !important; }}
  [data-testid="stTabs"] button {{
    color: {C['muted']} !important; background: transparent !important;
    border-bottom: 2px solid transparent !important; font-size: 13px !important;
  }}
  [data-testid="stTabs"] button[aria-selected="true"] {{
    color: {C['blue']} !important; border-bottom: 2px solid {C['blue']} !important;
  }}
  input, textarea {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important;
  }}
  [data-testid="stNumberInput"] button {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #2a2a2a !important;
  }}
  [data-testid="stNumberInput"] button:hover {{
    background-color: {C['blue']} !important; color: #000 !important;
  }}
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stMultiSelect"] > div > div {{
    background-color: #1a1a1a !important; color: {C['text']} !important;
    border: 1px solid #2a2a2a !important;
  }}
  [data-testid="stSelectbox"] svg {{ fill: {C['text']} !important; }}
  div[role="option"] {{ background-color: #1a1a1a !important; color: {C['text']} !important; }}
  div[role="option"]:hover {{ background-color: {C['blue']}22 !important; color: {C['blue']} !important; }}
  [data-testid="baseButton-primary"] {{
    background-color: {C['blue']} !important; color: #000 !important;
    font-weight: 700 !important; border: none !important; border-radius: 8px !important;
  }}
  [data-testid="baseButton-primary"]:hover {{ background-color: #33c6ff !important; }}
  button:not([data-testid="baseButton-primary"]) {{
    background-color: #141414 !important; color: {C['text']} !important;
    border: 1px solid #2a2a2a !important; border-radius: 8px !important;
  }}
  button:not([data-testid="baseButton-primary"]):hover {{
    background-color: #1e1e1e !important; border-color: {C['blue']}88 !important;
    color: {C['blue']} !important;
  }}
  [data-testid="stExpander"] {{
    background-color: #0a0a0a !important; border: 1px solid {C['border']} !important;
    border-radius: 10px !important;
  }}
  [data-testid="stExpander"] summary {{ color: {C['text']} !important; }}
  [data-testid="stExpander"] summary:hover {{ color: {C['blue']} !important; }}
  [data-testid="stDataFrame"] {{
    background-color: {C['card']} !important;
    border-radius: 10px !important; overflow: hidden !important;
  }}
  [data-testid="stFileUploader"] {{
    background-color: #0a0a0a !important; border: 1px dashed #2a2a2a !important;
    border-radius: 12px !important;
  }}
  .stCaption, small {{ color: {C['muted']} !important; }}
  [data-testid="stAlert"] {{
    background-color: #0a0a0a !important; border: 1px solid #2a2a2a !important;
    color: {C['text']} !important; border-radius: 10px !important;
  }}
  hr {{ border-color: {C['border']} !important; }}

  /* KPI Cards */
  .kpi-box {{
    background: {C['card']}; border: 1px solid {C['border']};
    border-radius: 14px; padding: 20px 24px; margin-bottom: 12px;
    transition: border-color 0.2s;
  }}
  .kpi-box:hover {{ border-color: #3a3a3a; }}
  .kpi-label {{
    font-size: 10px; color: {C['muted']}; text-transform: uppercase;
    letter-spacing: .1em; margin-bottom: 8px; font-weight: 500;
  }}
  .kpi-value {{ font-size: 26px; font-weight: 800; letter-spacing: -.02em; line-height: 1.1; }}

  /* Section titles */
  .section-title {{
    font-size: 10px; font-weight: 700; color: {C['muted']};
    text-transform: uppercase; letter-spacing: .12em;
    margin: 32px 0 16px; border-bottom: 1px solid {C['border']}; padding-bottom: 8px;
  }}

  /* Auth badges */
  .badge-admin {{
    display:inline-block; background:{C['green']}18; color:{C['green']};
    border:1px solid {C['green']}44; border-radius:20px; padding:4px 14px;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
  }}
  .badge-guest {{
    display:inline-block; background:{C['orange']}18; color:{C['orange']};
    border:1px solid {C['orange']}44; border-radius:20px; padding:4px 14px;
    font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
  }}

  /* Custom table */
  .custom-table {{ width:100%; border-collapse:separate; border-spacing:0 4px; }}
  .custom-table th {{
    font-size:10px; color:{C['muted']}; text-transform:uppercase; letter-spacing:.08em;
    padding:10px 16px; font-weight:600; background:transparent; border-bottom:1px solid {C['border']};
  }}
  .custom-table td {{
    padding:12px 16px; font-size:13px; color:{C['text']};
    background:{C['card2']}; border-top:1px solid transparent;
    border-bottom:1px solid {C['border']}11;
  }}
  .custom-table tr:hover td {{ background:#161616; }}
  .custom-table tr:first-child td {{ border-radius:10px 10px 0 0; }}
  .custom-table tr:last-child  td {{ border-radius:0 0 10px 10px; border-bottom:none; }}
  .rank-dot {{
    display:inline-block; width:8px; height:8px; border-radius:50%;
    margin-right:6px; vertical-align:middle;
  }}

  /* News cards */
  .news-card {{
    background:{C['card2']}; border:1px solid {C['border']}; border-radius:10px;
    padding:14px 18px; margin-bottom:8px; transition:border-color 0.2s;
  }}
  .news-card:hover {{ border-color:#3a3a3a; }}
  .news-title {{ font-size:14px; font-weight:600; color:{C['text']}; line-height:1.4; }}
  .news-meta  {{ font-size:11px; color:{C['muted']}; margin-top:6px; }}
  .source-badge {{
    display:inline-block; background:{C['blue']}18; color:{C['blue']};
    border-radius:4px; padding:2px 8px; font-size:10px; font-weight:600;
    text-transform:uppercase; margin-right:8px;
  }}
  .source-badge.trusted {{ background:{C['green']}18; color:{C['green']}; }}

  /* Top-3 cards */
  .top3-card {{
    background:{C['card2']}; border:1px solid {C['border']}; border-radius:12px;
    padding:16px; margin-bottom:8px;
  }}
  .top3-rank {{ font-size:22px; font-weight:800; }}
  .top3-name {{ font-size:13px; font-weight:600; margin:4px 0 2px; color:{C['text']}; }}
  .top3-score {{ font-size:11px; color:{C['muted']}; }}

  /* Upload hint */
  .upload-hint {{
    background:{C['card']}; border:1px dashed #2a2a2a; border-radius:14px;
    padding:40px; text-align:center; color:{C['muted']}; font-size:14px;
  }}
</style>
"""

"""
risk.py — VaR, Sharpe, drawdown, metriche di rischio.
"""
import numpy as np
import pandas as pd
from scipy import stats


def calc_risk(port_ret: pd.Series, total_value: float,
              confidence: float = 0.95, horizon: int = 1) -> dict:
    q       = 1 - confidence
    var_h   = -np.percentile(port_ret, q * 100) * np.sqrt(horizon)
    tail    = port_ret[port_ret <= np.percentile(port_ret, q * 100)]
    cvar_h  = -tail.mean() * np.sqrt(horizon) if len(tail) > 0 else var_h
    mu, sig = port_ret.mean(), port_ret.std()
    var_p   = -(mu * horizon + stats.norm.ppf(q) * sig * np.sqrt(horizon))
    ann_ret = (1 + port_ret).prod() ** (252 / max(len(port_ret), 1)) - 1
    vol     = sig * np.sqrt(252)
    sharpe  = ann_ret / vol if vol > 0 else np.nan
    down    = port_ret[port_ret < 0]
    sortino = ann_ret / (down.std() * np.sqrt(252)) if len(down) > 0 else np.nan
    cum     = (1 + port_ret).cumprod()
    dd      = (cum - cum.expanding().max()) / cum.expanding().max()
    return {
        "annual_return":    ann_ret,
        "volatility":       vol,
        "sharpe":           sharpe,
        "sortino":          sortino,
        "max_drawdown":     dd.min(),
        "hit_rate":         (port_ret > 0).mean(),
        "var_hist_pct":     var_h,
        "var_hist_eur":     var_h * total_value,
        "cvar_hist_eur":    cvar_h * total_value,
        "var_para_pct":     var_p,
        "var_para_eur":     var_p * total_value,
        "drawdown_series":  dd,
        "cumulative_returns": cum,
    }


def build_port_returns(prices: pd.DataFrame, value_weights: dict) -> pd.Series | None:
    """
    Costruisce la serie di rendimenti del portafoglio pesata per valore.
    value_weights: {ticker: valore_eur}
    """
    valid = {t: v for t, v in value_weights.items()
             if t in prices.columns and pd.notna(v) and v > 0}
    if not valid:
        return None
    total = sum(valid.values())
    w_arr = np.array([valid[t] / total for t in valid])
    ret_df = prices[list(valid.keys())].pct_change().dropna()
    if ret_df.empty:
        return None
    return (ret_df * w_arr).sum(axis=1)

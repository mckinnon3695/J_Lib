"""Forecast benchmarks. Every model must beat the no-change forecast.

Each benchmark is a function ``f(series, horizon) -> float`` forecasting the
log real price ``horizon`` months ahead from the end of ``series``. The
no-change benchmark here uses the monthly series as given (monthly-average
prices); the evaluation harness reports a robustness note since end-of-month
vs monthly-average benchmark definitions can flip results (Benyo et al. 2026).
"""

import numpy as np
import pandas as pd


def no_change(series: pd.Series, horizon: int) -> float:
    return float(series.iloc[-1])


def ar1_returns(series: pd.Series, horizon: int) -> float:
    """AR(1) on log returns, iterated forward."""
    r = series.diff().dropna()
    x, y = r.iloc[:-1].to_numpy(), r.iloc[1:].to_numpy()
    X = np.column_stack([np.ones_like(x), x])
    (a, b), *_ = np.linalg.lstsq(X, y, rcond=None)
    level, ret = float(series.iloc[-1]), float(r.iloc[-1])
    for _ in range(horizon):
        ret = a + b * ret
        level += ret
    return level


def futures_based(futures_curve: pd.DataFrame, asof: pd.Timestamp, horizon: int):
    """F_t^{(h)} as the forecast. Needs the external futures-curve file
    (see DATA_REQUEST_PROMPT.md); returns None when unavailable."""
    if futures_curve is None:
        return None
    sub = futures_curve[(futures_curve["date"] == asof)
                        & (futures_curve["months_ahead"] == horizon)]
    if sub.empty:
        return None
    return float(np.log(sub["settle_usd"].iloc[0]))

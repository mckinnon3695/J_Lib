"""Volatility model - kept separate from the level forecast.

GARCH(1,1) with Student-t innovations on monthly log returns (oil returns
are fat-tailed; t-errors fit materially better than normal).
"""

import numpy as np
import pandas as pd
from arch import arch_model


def fit_garch_t(ln_price: pd.Series):
    r = 100 * ln_price.diff().dropna()
    r.index = pd.DatetimeIndex(r.index)
    model = arch_model(r, vol="GARCH", p=1, q=1, dist="t")
    return model.fit(disp="off")


def vol_forecast(res, horizon: int = 12) -> pd.Series:
    """Annualized volatility forecast (%) per month ahead."""
    f = res.forecast(horizon=horizon, reindex=False)
    monthly_var = f.variance.iloc[0].to_numpy()
    ann = np.sqrt(monthly_var * 12)
    return pd.Series(ann, index=range(1, horizon + 1), name="ann_vol_pct")

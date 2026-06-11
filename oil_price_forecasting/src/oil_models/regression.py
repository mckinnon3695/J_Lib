"""Supply-demand regressions.

Two tiers:
1. ``adapted_regression`` - runs on the provided Kilian dataset alone:
   direct-projection OLS of the h-month-ahead change in the log real price on
   current production growth and real activity. Newey-West (HAC) errors.
2. ``eia_steo_regression`` - the full EIA STEO specification
   (delta price ~ delta US inventories + OECD stocks vs 4-yr seasonal norm +
   activity). Activates automatically once the external inventory files are
   present; otherwise returns None.
3. ``product_spread_forecast`` - the restricted (alpha=0) gasoline-spread
   model; needs external gasoline + spot price files.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import external_data


def _hac_ols(y: pd.Series, X: pd.DataFrame, h: int):
    Xc = sm.add_constant(X)
    return sm.OLS(y, Xc, missing="drop").fit(
        cov_type="HAC", cov_kwds={"maxlags": max(h, 1)})


def adapted_regression_fit(window: pd.DataFrame, horizon: int):
    """Fit the direct projection on an estimation window (used by the OOS
    harness and for in-sample inspection)."""
    dy = window["ln_real_oil_price"].shift(-horizon) - window["ln_real_oil_price"]
    X = window[["dprod_pct", "real_activity_igrea"]]
    return _hac_ols(dy, X, horizon)


def adapted_regression(window: pd.DataFrame, horizon: int) -> float:
    """Forecast of the log real price at horizon h from the window's end."""
    res = adapted_regression_fit(window, horizon)
    x_last = np.r_[1.0, window[["dprod_pct", "real_activity_igrea"]].iloc[-1].to_numpy()]
    return float(window["ln_real_oil_price"].iloc[-1] + res.params @ x_last)


def build_eia_dataset() -> pd.DataFrame | None:
    """Merge the external files into the EIA STEO regression frame."""
    spot = external_data.load("spot_prices_monthly.csv", quiet=True)
    us_inv = external_data.load("us_inventories_monthly.csv", quiet=True)
    oecd = external_data.load("oecd_inventories_monthly.csv", quiet=True)
    if spot is None or us_inv is None or oecd is None:
        return None
    df = (spot.merge(us_inv, on="date").merge(oecd, on="date")
              .set_index("date").asfreq("MS"))
    df["d_brent"] = df["brent_usd"].diff()
    df["d_us_inv"] = df["us_total_petroleum_stocks_mmb"].diff()
    norm = external_data.seasonal_norm(df["oecd_commercial_stocks_mmb"])
    df["oecd_dev_from_norm"] = df["oecd_commercial_stocks_mmb"] - norm
    return df.dropna(subset=["d_brent", "d_us_inv", "oecd_dev_from_norm"])


def eia_steo_regression(activity: pd.Series | None = None):
    """The EIA STEO monthly Brent regression. Returns the fitted results, or
    None until the external inventory data has been fetched."""
    df = build_eia_dataset()
    if df is None:
        print("[regression] EIA STEO inactive - fetch inventories/spot per DATA_REQUEST_PROMPT.md")
        return None
    X = df[["d_us_inv", "oecd_dev_from_norm"]].copy()
    if activity is not None:
        X["d_activity"] = activity.reindex(df.index).diff()
    return _hac_ols(df["d_brent"], X, h=1)


def product_spread_forecast(window_spot: pd.Series, gasoline: pd.Series,
                            horizon: int) -> float | None:
    """Restricted gasoline-spread model: P_{t+h} - P_t = beta * (gas_t - P_t),
    intercept forced to zero (the restriction is what makes it work
    out-of-sample)."""
    spread = (gasoline - window_spot).dropna()
    dy = (window_spot.shift(-horizon) - window_spot).dropna()
    common = spread.index.intersection(dy.index)
    if len(common) < 60:
        return None
    x, y = spread[common].to_numpy(), dy[common].to_numpy()
    beta = (x @ y) / (x @ x)
    return float(window_spot.iloc[-1] + beta * spread.iloc[-1])

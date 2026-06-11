"""Recursive (expanding-window) out-of-sample evaluation.

Protocol per docs/Oil_Model_Build_Guide.md section 7: estimate on data up to
t, forecast t+h, roll forward one month, re-estimate. Score = MSPE ratio vs
the no-change forecast, Diebold-Mariano (Harvey-Leybourne-Newbold small-sample
correction), and directional accuracy.
"""

import numpy as np
import pandas as pd
from scipy import stats


def recursive_forecasts(data: pd.DataFrame, target: str, models: dict,
                        start: str = "1992-01-01",
                        horizons=(1, 3, 6, 12)) -> dict[int, pd.DataFrame]:
    """models: name -> f(window_df, horizon) returning a target forecast.

    Returns per horizon a DataFrame of forecasts (one column per model) plus
    'actual' and 'last' (price at forecast origin), indexed by target date.
    """
    out = {h: [] for h in horizons}
    origins = data.index[(data.index >= pd.Timestamp(start))]
    for t in origins:
        window = data.loc[:t]
        for h in horizons:
            tgt_date = t + pd.DateOffset(months=h)
            if tgt_date not in data.index:
                continue
            row = {"date": tgt_date, "actual": data.loc[tgt_date, target],
                   "last": data.loc[t, target]}
            for name, f in models.items():
                row[name] = f(window, h)
            out[h].append(row)
    return {h: pd.DataFrame(rows).set_index("date") for h, rows in out.items()}


def dm_test(e1: np.ndarray, e2: np.ndarray, h: int) -> tuple[float, float]:
    """Diebold-Mariano with HLN correction; H0: equal MSPE. Negative stat
    favours model 1 (e1)."""
    d = e1**2 - e2**2
    n = len(d)
    dbar = d.mean()
    # Bartlett long-run variance with h-1 lags
    gamma0 = ((d - dbar) ** 2).mean()
    lrv = gamma0
    for lag in range(1, h):
        cov = ((d[lag:] - dbar) * (d[:-lag] - dbar)).mean()
        lrv += 2 * (1 - lag / h) * cov
    if lrv <= 0:
        lrv = gamma0
    dm = dbar / np.sqrt(lrv / n)
    hln = dm * np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    p = 2 * stats.t.sf(abs(hln), df=n - 1)
    return float(hln), float(p)


def scoreboard(forecasts: dict[int, pd.DataFrame], benchmark: str = "no-change") -> pd.DataFrame:
    """MSPE ratio vs benchmark, DM p-value, and directional accuracy per
    model and horizon."""
    rows = []
    for h, df in forecasts.items():
        bench_err = (df[benchmark] - df["actual"]).to_numpy()
        for col in df.columns:
            if col in ("actual", "last"):
                continue
            err = (df[col] - df["actual"]).to_numpy()
            ratio = (err**2).mean() / (bench_err**2).mean()
            if col == benchmark:
                dm_p = np.nan
            else:
                _, dm_p = dm_test(err, bench_err, h)
            pred_dir = np.sign(df[col] - df["last"])
            act_dir = np.sign(df["actual"] - df["last"])
            mask = act_dir != 0
            # no-change predicts no direction; accuracy is undefined for it
            da = np.nan if col == benchmark else (pred_dir[mask] == act_dir[mask]).mean()
            rows.append({"horizon": h, "model": col, "mspe_ratio": ratio,
                         "dm_pvalue": dm_p, "directional_accuracy": da,
                         "n": len(df)})
    return pd.DataFrame(rows).set_index(["horizon", "model"]).round(4)

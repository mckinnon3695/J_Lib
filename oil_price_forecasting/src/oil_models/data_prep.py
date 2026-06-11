"""Load and validate the Kilian VAR datasets.

Two datasets:
- ``kilian_var_dataset.csv`` — merged, model-ready monthly data 1974-01..2025-01.
- ``kilian2009_original_data.txt`` — Kilian's original AER (2009) data,
  1973-02..2007-12, three columns in his order [dprod_pct, rea, real price].
"""

import numpy as np
import pandas as pd

from . import DATA_RAW

VAR_COLUMNS = ["dprod_pct", "real_activity_igrea", "ln_real_oil_price"]


def load_kilian_dataset() -> pd.DataFrame:
    """Full-sample model-ready dataset, first (blank-dprod) row dropped."""
    df = pd.read_csv(DATA_RAW / "kilian_var_dataset.csv", parse_dates=["date"])
    df = df.set_index("date").asfreq("MS")
    df = df.dropna(subset=["dprod_pct"])
    _validate_kilian(df)
    return df


def load_kilian_original() -> pd.DataFrame:
    """Kilian's published 1973-02..2007-12 data in his exact column order.

    The real price column is Kilian's percent deviation form (100 x log real
    price, demeaned); it differs from the full dataset's ln_real_oil_price by
    scale and centering, which does not affect VAR dynamics.
    """
    raw = np.loadtxt(DATA_RAW / "kilian2009_original_data.txt")
    if raw.shape[1] != 3:
        raise ValueError(f"expected 3 columns, got {raw.shape[1]}")
    idx = pd.date_range("1973-02-01", periods=raw.shape[0], freq="MS")
    return pd.DataFrame(raw, index=idx, columns=VAR_COLUMNS)


def _validate_kilian(df: pd.DataFrame) -> None:
    missing = [c for c in VAR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"kilian dataset missing columns: {missing}")
    if df[VAR_COLUMNS].isna().any().any():
        raise ValueError("NaNs in model variables after dropping first row")
    # Sanity: known disruption episodes should show production drops and the
    # activity index should trough in the 2008-09 and 2020 recessions.
    if df.loc["2020-03":"2020-06", "dprod_pct"].min() > -2:
        raise ValueError("expected a large production drop in 2020")
    if df.loc["2008-10":"2009-12", "real_activity_igrea"].min() > 0:
        raise ValueError("expected negative real activity in 2008-09")


def summary(df: pd.DataFrame) -> pd.DataFrame:
    return df[VAR_COLUMNS].describe().T[["count", "mean", "std", "min", "max"]]

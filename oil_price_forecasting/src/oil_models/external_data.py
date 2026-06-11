"""Loaders for data fetched on the user's PC per DATA_REQUEST_PROMPT.md.

Every file lives in ``data/external/`` and follows an exact schema. Loaders
return None (with a console note) when a file is absent, so models that need
it degrade gracefully; they raise with a pointer to the prompt when a file
exists but is malformed.
"""

import pandas as pd

from . import DATA_EXTERNAL

# filename -> (required columns, description)
SCHEMAS = {
    "spot_prices_monthly.csv": (
        ["date", "brent_usd", "wti_usd"],
        "Monthly average Brent & WTI spot, USD/bbl, 1987-01 .. latest"),
    "us_inventories_monthly.csv": (
        ["date", "us_total_petroleum_stocks_mmb"],
        "Monthly US total petroleum stocks (crude + products, incl. SPR excluded), million bbl"),
    "oecd_inventories_monthly.csv": (
        ["date", "oecd_commercial_stocks_mmb"],
        "Monthly OECD commercial petroleum stocks, million bbl"),
    "gasoline_monthly.csv": (
        ["date", "gasoline_usd_bbl"],
        "Monthly US conventional gasoline spot, USD/bbl (USD/gal x 42)"),
    "futures_curve_monthly.csv": (
        ["date", "symbol", "months_ahead", "settle_usd"],
        "Month-end CL and BZ futures settles by months-ahead (1..24)"),
    "world_production_monthly.csv": (
        ["date", "world_crude_prod_kbd"],
        "Monthly world crude production, thousand bbl/day, through latest"),
    "cpi_monthly.csv": (
        ["date", "cpi"],
        "US CPI (CPIAUCSL), monthly, through latest"),
    "igrea_monthly.csv": (
        ["date", "igrea"],
        "Kilian/Dallas Fed IGREA index, monthly, through latest"),
}


def load(name: str, quiet: bool = False):
    if name not in SCHEMAS:
        raise KeyError(f"unknown external dataset {name!r}; see SCHEMAS")
    path = DATA_EXTERNAL / name
    cols, desc = SCHEMAS[name]
    if not path.exists():
        if not quiet:
            print(f"[external] {name} not present ({desc}). "
                  f"Fetch it with DATA_REQUEST_PROMPT.md; dependent models stay inactive.")
        return None
    df = pd.read_csv(path)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name} is missing columns {missing}; expected {cols}. "
            "Regenerate it per DATA_REQUEST_PROMPT.md.")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def seasonal_norm(stocks: pd.Series, years: int = 4) -> pd.Series:
    """EIA-style norm: for calendar month m, the average of that month's
    level over the prior ``years`` years. Returns the deviation regressor's
    norm component (NaN until enough history)."""
    norm = pd.Series(index=stocks.index, dtype=float)
    for ts in stocks.index:
        past = [ts - pd.DateOffset(years=y) for y in range(1, years + 1)]
        vals = stocks.reindex(past).dropna()
        norm[ts] = vals.mean() if len(vals) == years else float("nan")
    return norm


def status() -> pd.DataFrame:
    rows = [{"file": n, "present": (DATA_EXTERNAL / n).exists(), "description": d}
            for n, (_, d) in SCHEMAS.items()]
    return pd.DataFrame(rows).set_index("file")

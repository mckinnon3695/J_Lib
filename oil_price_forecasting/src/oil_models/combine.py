"""Equal-weight forecast combination - the literature's most robust result.

Estimating "optimal" weights overfits; the simple average of member point
forecasts is more stable and accurate out-of-sample (Baumeister-Kilian 2015).
"""

import pandas as pd


def equal_weight(forecasts: dict[int, pd.DataFrame], members: list[str],
                 name: str = "combination") -> dict[int, pd.DataFrame]:
    """Add an equal-weight combination column to each horizon's forecast
    table, averaging whichever members are present and non-null."""
    for df in forecasts.values():
        cols = [m for m in members if m in df.columns]
        df[name] = df[cols].mean(axis=1)
    return forecasts

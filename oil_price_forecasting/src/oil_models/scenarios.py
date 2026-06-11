"""Hormuz disruption -> conditional oil-price scenarios through the SVAR.

The satellite-measured collapse in laden crude transits (from 2026-02-28) is
translated into a sequence of structural oil-supply shocks and pushed through
the estimated impulse responses. Because the measured transit loss (~19 mb/d,
~23% of world production) is far larger than any shock in the estimation
sample, results are produced for several pass-through fractions: how much of
the lost transit flow actually leaves the market (the rest rerouted, drawn
from storage on the buyer side, or backfilled by other producers).

The linear VAR extrapolates well outside its estimation range at high
pass-through - those paths are upper bounds on the model's own terms, not
point predictions.
"""

import numpy as np
import pandas as pd

from . import kilian_var as kv
from .hormuz import WORLD_PRODUCTION_BPD

# Pass-through fractions: 1.0 = the full measured transit loss hits world supply.
PASS_THROUGH = {"25% pass-through": 0.25, "50% pass-through": 0.50,
                "full measured loss": 1.00}


def monthly_supply_loss_pct(hormuz_monthly: pd.DataFrame) -> pd.Series:
    """Lost crude flow per month as a % of world production (level loss)."""
    bpd_lost = hormuz_monthly["hormuz_crude_shortfall_mmb"] * 1e6 / hormuz_monthly.index.days_in_month
    pct = 100 * bpd_lost / WORLD_PRODUCTION_BPD
    return pct[pct > 0.05]


def supply_shock_path(model: kv.SVAR, level_loss_pct: pd.Series,
                      pass_through: float = 1.0,
                      precautionary_sd: float = 0.0) -> np.ndarray:
    """Map a monthly % level loss of world supply to structural shock units.

    dprod_pct is a monthly growth rate, so the shock each month is the
    *change* in the level loss. The structural supply shock (in standard
    deviations) is that growth shock divided by its impact coefficient
    P[0, 0]. Optionally adds a precautionary (oil-specific) demand shock of
    ``precautionary_sd`` standard deviations in the first disruption month -
    the fear/inventory premium that accompanied 1979 and 1990.
    """
    loss = pass_through * level_loss_pct.to_numpy()
    dprod_shock = -np.diff(np.concatenate([[0.0], loss]))  # growth-rate hit
    eps = np.zeros((len(dprod_shock), model.k))
    eps[:, 0] = dprod_shock / model.P[0, 0]
    if precautionary_sd:
        eps[0, 2] += precautionary_sd
    return eps


def run_scenarios(model: kv.SVAR, hormuz_monthly: pd.DataFrame,
                  horizon: int = 36, precautionary_sd: float = 0.0,
                  ref_cpi: float | None = None) -> pd.DataFrame:
    """Real-price paths (levels, not logs) under each pass-through scenario.

    The estimation sample ends before the disruption, so the path up to the
    first shock month is the model's unconditional forecast; shocks are then
    applied in the months the satellite data dates them. Pass ``ref_cpi``
    (e.g. the last observed CPI) to express the real price in constant
    dollars of that date instead of the deflated price/CPI index.
    """
    loss = monthly_supply_loss_pct(hormuz_monthly)
    base = kv.forecast(model, horizon)
    first_shock = loss.index[0]
    if first_shock <= model.data.index[-1]:
        raise ValueError("disruption overlaps estimation sample; re-estimate first")
    offset = base.index.get_loc(first_shock)

    out = {"baseline (no disruption)": np.exp(base["ln_real_oil_price"])}
    for label, pt in PASS_THROUGH.items():
        eps = supply_shock_path(model, loss, pt, precautionary_sd)
        padded = np.vstack([np.zeros((offset, model.k)), eps])
        cond = kv.scenario_forecast(model, padded, horizon)
        out[label] = np.exp(cond["ln_real_oil_price"])
    df = pd.DataFrame(out)
    if ref_cpi is not None:
        df *= ref_cpi
    df.index.name = "date"
    return df


def scenario_summary(paths: pd.DataFrame, hormuz_monthly: pd.DataFrame) -> pd.DataFrame:
    """Peak price impact per scenario vs the no-disruption baseline."""
    base = paths["baseline (no disruption)"]
    rows = []
    for col in paths.columns:
        if col == base.name:
            continue
        ratio = paths[col] / base
        rows.append({
            "scenario": col,
            "peak_price_uplift_pct": 100 * (ratio.max() - 1),
            "peak_month": ratio.idxmax().strftime("%Y-%m"),
            "uplift_12m_after_shock_pct": 100 * (ratio.iloc[-1] - 1),
        })
    return pd.DataFrame(rows).set_index("scenario")

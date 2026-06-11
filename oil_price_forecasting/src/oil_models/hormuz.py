"""Parse and analyze the Hormuz satellite tanker-transit workbook (Boil_1.xlsx).

The ``Data`` sheet holds daily deadweight tonnes (DWT) of tankers observed
transiting the Strait of Hormuz, by tanker type and direction, May 2025 to
May 2026. West>East rows are the laden export flow out of the Gulf; the
workbook converts DWT to barrels of oil equivalent (BOE) with per-type
factors. Crude transits collapse ~97% from 2026-02-28 ("Start of Hormuz
Decline").

Outputs: a tidy daily table, monthly aggregates ready to merge with the
Kilian VAR dataset, baseline/shortfall metrics, days-of-consumption, and an
implied inventory-draw series (the Kilian-Murphy delta-inventory proxy).
"""

from dataclasses import dataclass

import numpy as np
import openpyxl
import pandas as pd

from . import DATA_RAW, DATA_PROCESSED

BOIL_XLSX = DATA_RAW / "Boil_1.xlsx"

# DWT -> BOE factors from the workbook's "DWT Conversion" block.
BOE_PER_DWT = {
    "Crude Oil Tanker": 7.33,
    "LNG Tanker": 8.001,
    "LPG Tanker": 7.542,
}

DECLINE_START = pd.Timestamp("2026-02-28")

# bbl/day consumption constants from the workbook's "Key Points" block.
CONSUMPTION_BPD = {
    "China": 20_300_000,
    "USA": 16_100_000,
    "EU": 10_500_000,
    "Global": 104_600_000,
}

WORLD_PRODUCTION_BPD = 82_000_000  # approx. world crude production, EIA 2025


def parse_boil(path=BOIL_XLSX) -> pd.DataFrame:
    """Tidy daily table: date, tanker_type, direction, dwt, boe.

    direction is 'both' for the per-type total rows, else 'east_west' /
    'west_east'. BOE is NaN for types without a workbook conversion factor
    (Chemical / Products), matching the workbook's own conversion table.
    """
    ws = openpyxl.load_workbook(path, data_only=True)["Data"]
    rows = list(ws.iter_rows(values_only=True))
    dates = pd.to_datetime(rows[0][2:], format="%m/%d/%Y")

    records = []
    current_type = None
    for row in rows[1:]:
        level, label = row[0], row[1]
        if level is None:
            break  # past the transit block, into the workbook's calc blocks
        values = [v if isinstance(v, (int, float)) else 0.0 for v in row[2 : 2 + len(dates)]]
        if level == 0:
            continue  # grand total across types; recomputable
        if level == 1:
            current_type = label
            direction = "both"
        else:
            direction = "east_west" if "East>West" in label else "west_east"
        factor = BOE_PER_DWT.get(current_type)
        for d, v in zip(dates, values):
            records.append(
                {
                    "date": d,
                    "tanker_type": current_type,
                    "direction": direction,
                    "dwt": float(v),
                    "boe": float(v) * factor if factor else np.nan,
                }
            )
    df = pd.DataFrame(records).sort_values(["tanker_type", "direction", "date"])
    return df.reset_index(drop=True)


def daily_series(tidy: pd.DataFrame, tanker_type="Crude Oil Tanker", direction="west_east") -> pd.Series:
    """One daily BOE series, indexed by date."""
    sub = tidy[(tidy.tanker_type == tanker_type) & (tidy.direction == direction)]
    return sub.set_index("date")["boe"].asfreq("D")


@dataclass
class DisruptionMetrics:
    tanker_type: str
    baseline_boe_per_day: float
    post_boe_per_day: float
    decline_pct: float
    n_post_days: int
    cumulative_shortfall_boe: float
    days_of_consumption: dict


def disruption_metrics(tidy: pd.DataFrame, tanker_type="Crude Oil Tanker",
                       decline_start=DECLINE_START) -> DisruptionMetrics:
    """Baseline vs post-decline flow and the cumulative supply shortfall.

    Uses the laden (West>East) export flow. The baseline is the simple
    pre-decline daily mean, matching the workbook's "Historical Average
    Before feb 24" methodology.
    """
    s = daily_series(tidy, tanker_type, "west_east")
    pre, post = s[s.index < decline_start], s[s.index >= decline_start]
    baseline, post_mean = pre.mean(), post.mean()
    shortfall = float((baseline - post).clip(lower=0).sum())
    days_of = {
        region: shortfall / bpd for region, bpd in CONSUMPTION_BPD.items()
    }
    return DisruptionMetrics(
        tanker_type=tanker_type,
        baseline_boe_per_day=float(baseline),
        post_boe_per_day=float(post_mean),
        decline_pct=float(100 * (1 - post_mean / baseline)),
        n_post_days=len(post),
        cumulative_shortfall_boe=shortfall,
        days_of_consumption=days_of,
    )


def monthly_aggregates(tidy: pd.DataFrame) -> pd.DataFrame:
    """Monthly Hormuz series shaped to merge onto the Kilian VAR dataset.

    Columns per type: mean BOE/day, total BOE, shortfall vs pre-decline
    baseline, and an implied inventory draw (negative = stocks drawn down
    east of Hormuz as cargoes stop arriving) in million barrels.
    """
    frames = {}
    for ttype in BOE_PER_DWT:
        s = daily_series(tidy, ttype, "west_east")
        baseline = s[s.index < DECLINE_START].mean()
        m = s.resample("MS").agg(["mean", "sum", "count"])
        key = ttype.split()[0].lower()  # crude / lng / lpg
        frames[f"hormuz_{key}_boepd"] = m["mean"]
        frames[f"hormuz_{key}_total_boe"] = m["sum"]
        shortfall = (baseline - s).clip(lower=0)
        shortfall[s.index < DECLINE_START] = 0.0
        frames[f"hormuz_{key}_shortfall_mmb"] = shortfall.resample("MS").sum() / 1e6
    out = pd.DataFrame(frames)
    out["hormuz_implied_inv_draw_mmb"] = -out[
        [c for c in out.columns if c.endswith("shortfall_mmb")]
    ].sum(axis=1)
    # Supply-shock size: lost crude flow as % of world production
    out["hormuz_supply_shock_pct"] = (
        100 * (out["hormuz_crude_shortfall_mmb"] * 1e6 / out.index.days_in_month)
        / WORLD_PRODUCTION_BPD
    )
    out.index.name = "date"
    return out


def validate_against_workbook(tidy: pd.DataFrame) -> dict:
    """Reproduce the workbook's own headline numbers as a parsing check.

    The Data sheet computes (as of 2026-06-02, 94 days into the decline):
    crude baseline 19,883,899.78 BOE/day and an estimated crude shortfall of
    1,827,513,950 barrels (= baseline*94 - actual BOE since the decline).
    """
    s = daily_series(tidy, "Crude Oil Tanker", "west_east")
    baseline = float(s[s.index < DECLINE_START].mean())
    post = s[s.index >= DECLINE_START]
    actual_since = float(post.sum())
    shortfall_94d = baseline * 94 - actual_since
    return {
        "baseline_boe_per_day": baseline,
        "workbook_baseline": 19_883_899.78,
        "baseline_match_pct": 100 * baseline / 19_883_899.78,
        "actual_boe_since_decline": actual_since,
        "workbook_actual": 41_572_630.09,
        "shortfall_94d_boe": shortfall_94d,
        "workbook_shortfall": 1_827_513_950.0,
        "shortfall_match_pct": 100 * shortfall_94d / 1_827_513_950.0,
    }


def build_processed(force=False) -> pd.DataFrame:
    """Write tidy daily + monthly CSVs to data/processed; return monthly."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    daily_path = DATA_PROCESSED / "hormuz_daily.csv"
    monthly_path = DATA_PROCESSED / "hormuz_monthly.csv"
    tidy = parse_boil()
    monthly = monthly_aggregates(tidy)
    if force or not daily_path.exists():
        tidy.to_csv(daily_path, index=False)
    if force or not monthly_path.exists():
        monthly.to_csv(monthly_path)
    return monthly

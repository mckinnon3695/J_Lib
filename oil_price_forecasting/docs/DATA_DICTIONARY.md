# Kilian VAR — Data Dictionary

## The file you'll actually use: `kilian_var_dataset.csv`

Monthly, 1974-01 to 2025-01 (613 observations). One row per month. This is the merged, model-ready dataset.

| Column | Meaning | Units | Source | Use in the VAR |
|---|---|---|---|---|
| `date` | First day of the month | YYYY-MM-DD | — | index |
| `oil_production_kbd_sa` | World crude oil production, seasonally adjusted | thousand barrels/day | EIA | raw input for variable 1 |
| `real_activity_igrea` | Kilian index of global real economic activity (corrected, Kilian 2019) | % deviation from trend | Dallas Fed / FRED (IGREA) | **variable 2** (use as-is) |
| `oil_price_usd` | Nominal crude oil price (US refiners' acquisition cost) | USD/barrel | EIA | raw input for variable 3 |
| `us_cpi` | US Consumer Price Index (all urban, SA) | index, 1982-84=100 | FRED (CPIAUCSL) | deflator for variable 3 |
| `dprod_pct` | Pre-computed: 100 × Δln(production) | percent | derived | **variable 1** (ready to use) |
| `real_oil_price` | Pre-computed: 100 × price / CPI | index | derived | (level form, optional) |
| `ln_real_oil_price` | Pre-computed: ln(price / CPI) | log | derived | **variable 3** (ready to use) |

The three model variables, in order, are: **`dprod_pct`, `real_activity_igrea`, `ln_real_oil_price`**. Everything else is raw material or a cross-check. The first row of `dprod_pct` is blank because a change needs a prior month — drop that first row when estimating.

## Supporting / raw files (so you can rebuild or audit)

- `VAR_data_assembled.csv` — the fuller assembled set this was distilled from (also has world industrial production `wip` as an alternative activity proxy, and a non-seasonally-adjusted production column).
- `EIA_world_oil_production.csv` — standalone world crude production (SA and NSA).
- `EIA_oil_prices.csv` — standalone oil price (SA and NSA).
- `FRED_monthly.csv` — standalone IGREA (`rea`) and CPI (`cpi`).
- `IGREA.csv`, `CPIAUCSL.csv`, `MCOILWTICO.csv` — the original single-series pulls straight from FRED (IGREA, US CPI, and WTI spot as an alternative price series).
- `kilian2009_original_data.txt` — Kilian's **original** AER (2009) data, three columns in his exact order [Δprod%, rea, real price], 1973–2007. Use this if you want to reproduce the published paper's numbers exactly before extending to 2025.
- `kilian2009_readme.txt` — Kilian's note describing the original files.

## Sources & faithful-replication notes

- Real activity index: Dallas Fed IGREA — https://www.dallasfed.org/research/igrea (also FRED series `IGREA`).
- Assembled data and EIA pulls mirror Ryan (2024) replication of Kilian (2009): https://github.com/richryan/jcre-oil
- Kilian's own data page: https://sites.google.com/site/lkilian2019/research/data-sets
- Original paper: Kilian (2009), *American Economic Review* 99(3).
- Note on the price series: Kilian uses the **US refiners' acquisition cost** of crude (here `oil_price_usd`). `MCOILWTICO.csv` (WTI) is provided as a common alternative, but for faithful replication use the refiners' acquisition cost.
- Note on units: the production column is labeled "millions_barrels_day" in the upstream file but the values (~82,000) are **thousand barrels/day**. This does not affect the VAR, because variable 1 is a log-change (percent), which is unit-free.

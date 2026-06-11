# Data Request Prompt

Copy everything inside the block below and paste it to Claude running on a
machine with internet access (and, for the futures curve, a logged-in IBKR
Gateway / TWS). It will produce the CSVs that activate the EIA STEO
regression, the product-spread model, the futures benchmark, and post-2025
re-estimation of the VAR. Drop the resulting files into
`oil_price_forecasting/data/external/` and re-run `python scripts/run_all.py`.

---

```
I need you to download oil-market data and save it as CSV files with EXACT
filenames and column schemas (lowercase snake_case headers, dates as the
first of the month in YYYY-MM-DD, sorted ascending, no missing months, no
thousands separators). Free sources: FRED (https://fred.stlouisfed.org —
CSV endpoint https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIES),
EIA Open Data API v2 (https://www.eia.gov/opendata/ — free API key), and
the Dallas Fed. For futures I have IBKR Gateway running locally
(Client Portal API at https://localhost:5000/v1/api, ignore the
self-signed certificate).

Create these 8 files:

1. spot_prices_monthly.csv — columns: date, brent_usd, wti_usd
   Monthly average spot prices, USD/barrel, from 1987-05 through the latest
   month. FRED series: MCOILBRENTEU (Brent), MCOILWTICO (WTI).

2. cpi_monthly.csv — columns: date, cpi
   US CPI all urban consumers, seasonally adjusted (FRED: CPIAUCSL),
   1947-01 through latest.

3. igrea_monthly.csv — columns: date, igrea
   Kilian index of global real economic activity, corrected version
   (FRED: IGREA, or Dallas Fed https://www.dallasfed.org/research/igrea),
   1968-01 through latest.

4. world_production_monthly.csv — columns: date, world_crude_prod_kbd
   World crude oil production including lease condensate, thousand
   barrels/day, monthly, 1973-01 through latest. Source: EIA international
   data API (activityId=1 production, productId=55 crude incl. condensate,
   countryRegionId=WORL) or EIA International Energy Statistics download.

5. us_inventories_monthly.csv — columns: date, us_total_petroleum_stocks_mmb
   US ending stocks of crude oil and petroleum products EXCLUDING the
   Strategic Petroleum Reserve, million barrels, monthly, 1990-01 through
   latest. EIA petroleum API, series "U.S. Ending Stocks excluding SPR of
   Crude Oil and Petroleum Products" (legacy id PET.MTESTUS1.M).

6. oecd_inventories_monthly.csv — columns: date, oecd_commercial_stocks_mmb
   OECD commercial petroleum inventories (end of period), million barrels,
   monthly, as far back as available (1990s) through latest. EIA STEO API
   series PASC_OECD_T3 (STEO Table 3a "OECD Commercial Inventory").

7. gasoline_monthly.csv — columns: date, gasoline_usd_bbl
   US Gulf Coast conventional regular gasoline spot price, monthly average,
   converted to USD/barrel (price per gallon x 42), 1986-06 through latest.
   EIA series EER_EPMRU_PF4_RGC_DPG (monthly frequency).

8. futures_curve_monthly.csv — columns: date, symbol, months_ahead, settle_usd
   Month-end settlement prices for WTI (symbol CL, NYMEX) and Brent
   (symbol BZ) futures, months_ahead = 1..24, for each month-end from as far
   back as you can get through latest. Preferred source: IBKR Client Portal
   API (search contracts via /iserver/secdef/search, history via
   /iserver/marketdata/history). If historical month-end curves are hard to
   assemble from IBKR, fall back to EIA "Cushing OK Crude Oil Future
   Contract 1-4" (PET.RCLC1.M .. PET.RCLC4.M) for months_ahead 1..4 with
   symbol CL, and note the limitation.

Validation before you finish: each file loads with pandas, has the exact
column names above, monthly ascending dates with no gaps, and sensible
magnitudes (Brent 10-140, stocks in the hundreds/thousands of million bbl,
production ~55,000-85,000 kbd). Print a 3-line preview of each file.
```

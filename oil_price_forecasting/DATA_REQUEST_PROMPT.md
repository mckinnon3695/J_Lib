# Data Request Prompt (v2)

Copy everything inside the block below and paste it to Claude running on a
machine with internet access (and, for futures/options, a logged-in IBKR
Gateway / TWS — or just export from your broker/Bloomberg manually). Drop
the resulting files into `oil_price_forecasting/data/external/` and re-run:

```bash
python scripts/run_all.py && python scripts/options_analysis.py
```

v2 additions over v1: daily spot prices (end-of-month benchmark robustness),
the refiners' acquisition cost series (extends the Kilian price series past
2025), and wide-strike option chains (the current export stops near $100,
which forces extrapolation of exactly the tail we care about).

---

```
I need you to download oil-market data and save it as CSV files with EXACT
filenames and column schemas (lowercase snake_case headers, dates in
YYYY-MM-DD, sorted ascending, no missing periods, no thousands separators).
Monthly files use the first of the month as the date. Free sources: FRED
(https://fred.stlouisfed.org — CSV endpoint
https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIES), EIA Open Data
API v2 (https://www.eia.gov/opendata/ — free API key), and the Dallas Fed.

For futures and options, Interactive Brokers Trader Workstation is running
locally with the socket API enabled: host 127.0.0.1, port 7947 (custom -
not the default 7496/4001), Read-Only API mode (market data works fine;
never attempt to place orders). Connect with the ib_async Python library
(pip install ib_async; ib.connect('127.0.0.1', 7947, clientId=11)).
If a live market-data subscription is missing for a contract, fall back to
delayed data via ib.reqMarketDataType(3) and note it in the output. Respect
IBKR pacing limits: request quotes in batches (~50 contracts at a time)
with short pauses, and use snapshot=True for one-shot quotes.

Create these 11 files:

1. spot_prices_monthly.csv — columns: date, brent_usd, wti_usd
   Monthly average spot prices, USD/barrel, 1987-05 through the latest
   month. FRED: MCOILBRENTEU (Brent), MCOILWTICO (WTI).

2. spot_prices_daily.csv — columns: date, brent_usd, wti_usd
   DAILY spot prices, USD/barrel, 1987-05 through latest. FRED:
   DCOILBRENTEU and DCOILWTICO. Keep business days only; leave a price
   blank if missing rather than filling it.

3. cpi_monthly.csv — columns: date, cpi
   US CPI all urban consumers, seasonally adjusted (FRED: CPIAUCSL),
   1947-01 through latest.

4. igrea_monthly.csv — columns: date, igrea
   Kilian index of global real economic activity, corrected version
   (FRED: IGREA, or Dallas Fed https://www.dallasfed.org/research/igrea),
   1968-01 through latest.

5. world_production_monthly.csv — columns: date, world_crude_prod_kbd
   World crude oil production including lease condensate, thousand
   barrels/day, monthly, 1973-01 through latest. EIA international data
   API (activityId=1, productId=55 crude incl. condensate,
   countryRegionId=WORL).

6. rac_price_monthly.csv — columns: date, rac_usd
   US crude oil composite acquisition cost by refiners, USD/barrel,
   monthly, 1974-01 through latest. EIA petroleum API, "U.S. Crude Oil
   Composite Acquisition Cost by Refiners" (legacy id PET.R0000____3.M).
   This extends the exact price concept the Kilian VAR dataset uses.

7. us_inventories_monthly.csv — columns: date, us_total_petroleum_stocks_mmb
   US ending stocks of crude oil and petroleum products EXCLUDING the
   Strategic Petroleum Reserve, million barrels, monthly, 1990-01 through
   latest. EIA petroleum API (legacy id PET.MTESTUS1.M).

8. oecd_inventories_monthly.csv — columns: date, oecd_commercial_stocks_mmb
   OECD commercial petroleum inventories (end of period), million barrels,
   monthly, as far back as available through latest. EIA STEO API series
   PASC_OECD_T3 (STEO Table 3a "OECD Commercial Inventory").

9. gasoline_monthly.csv — columns: date, gasoline_usd_bbl
   US Gulf Coast conventional regular gasoline spot, monthly average,
   converted to USD/barrel (price per gallon x 42), 1986-06 through
   latest. EIA series EER_EPMRU_PF4_RGC_DPG (monthly).

10. futures_curve_monthly.csv — columns: date, symbol, months_ahead, settle_usd
    Month-end settlement prices for WTI (symbol CL, exchange NYMEX) and
    Brent (symbol BZ) futures, months_ahead = 1..24, each month-end as far
    back as obtainable through latest. Via TWS: qualify each listed
    contract month (Future(symbol='CL', exchange='NYMEX',
    lastTradeDateOrContractMonth=...)), pull daily bars with
    ib.reqHistoricalData (whatToShow='TRADES', 1 day bars), and keep each
    month's last business day. Note IBKR holds expired-future history for
    roughly 2 years only. For deeper history, fall back to EIA "Cushing OK
    Crude Oil Future Contract 1-4" (PET.RCLC1.M..PET.RCLC4.M) as symbol
    CL, months_ahead 1..4, and note the limitation.

11. options_chains.csv — columns: snapshot_date, contract, expiry_date,
    days, future, strike, side, bid, ask, last, iv, volume
    A fresh snapshot of WTI (CL) futures option chains from IBKR via TWS,
    one row per option quote. side is the string "call" or "put"; days =
    calendar days from snapshot to expiry; future = the underlying futures
    price at the snapshot; iv = implied vol in percent (e.g. 47.3), taken
    from IBKR's model greeks (ticker.modelGreeks.impliedVol x 100, or the
    bid/ask greeks average). Recipe: ib.reqSecDefOptParams for the chain
    parameters, then FuturesOption contracts per expiry/strike/right on
    NYMEX, qualified and quoted in batches. Requirements:
    - ALL monthly expiries listed out to at least 12 months.
    - The WIDEST strike range available — deep out-of-the-money wings
      matter most; go to at least $150 strikes on the call side and $40 on
      the put side where listed, even if bids are pennies.
    - Take the snapshot during US trading hours if possible so quotes are
      live and two-sided; if only delayed data is available, say so.
    - If Brent (BZ) chains are accessible, append them too (same columns;
      contract distinguishes them).

Validation before you finish: each file loads with pandas, has the exact
column names above, dates ascending with no gaps (monthly files), and
sensible magnitudes (Brent 10-140 USD, stocks in hundreds/thousands of
million bbl, production ~55,000-85,000 kbd, implied vols 15-120%). Print a
3-line preview of each file and a one-line summary of its date range.
```

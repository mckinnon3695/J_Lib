"""Options-implied (risk-neutral) densities for WTI futures - the
forward-looking tail-risk gauge.

Input: Bloomberg-style option-chain export (data/raw/Oil_Futures_Options.xlsx),
one sheet per expiry with calls (left block) and puts (right block):
Ticker, Strike, Bid, Ask, Last, IVM, Volm. A header row carries the expiry,
days to expiry, and the underlying future, e.g.
"Jul-26 (6d 6/16/26); CSize 1000; CLN6 88.83".

Method (Breeden-Litzenberger): build an out-of-the-money implied-vol smile
from mid quotes, smooth it with a spline, price calls on a dense strike grid
with Black-76, and differentiate twice: f(K) = e^{rT} d2C/dK2. The result is
the *risk-neutral* density - it embeds risk premia, so tail probabilities
read from it are upper bounds on real-world ("physical") probabilities;
that bias is largest exactly in feared states like a supply crisis.
"""

import re
from dataclasses import dataclass

import numpy as np
import openpyxl
import pandas as pd
from scipy.interpolate import UnivariateSpline
from scipy.stats import norm

from . import DATA_RAW

OPTIONS_XLSX = DATA_RAW / "Oil_Futures_Options.xlsx"
RISK_FREE = 0.04  # discounting has negligible effect on the density shape

HEADER_RE = re.compile(
    r"(?P<label>\w+-\d+)\s*\((?P<days>\d+)d\s+(?P<expiry>[\d/]+)\).*?"
    r"(?P<contract>[A-Z]{3}\d)\s+(?P<future>[\d.]+)")


@dataclass
class Chain:
    label: str            # e.g. Jul-26
    contract: str         # e.g. CLN6
    expiry: pd.Timestamp
    days: int
    future: float
    quotes: pd.DataFrame  # strike, side, bid, ask, mid, iv, volume

    @property
    def years(self):
        return self.days / 365.0


def parse_chains(path=OPTIONS_XLSX) -> list[Chain]:
    """Sheets can hold several expiry sections; each header row starts a new
    chain and the quote rows that follow belong to it."""
    wb = openpyxl.load_workbook(path, data_only=True)
    chains = []

    def emit(meta, records):
        if meta and records:
            chains.append(Chain(
                label=meta["label"], contract=meta["contract"],
                expiry=pd.Timestamp(meta["expiry"]), days=int(meta["days"]),
                future=float(meta["future"]),
                quotes=pd.DataFrame(records).assign(
                    mid=lambda d: (d.bid + d.ask) / 2)))

    for name in wb.sheetnames:
        meta, records = None, []
        for row in wb[name].iter_rows(values_only=True):
            if isinstance(row[0], str):
                m = HEADER_RE.search(row[0])
                if m:
                    emit(meta, records)
                    meta, records = m.groupdict(), []
                    continue
            if meta and isinstance(row[1], (int, float)):
                for off, side in ((0, "call"), (7, "put")):
                    strike, bid, ask, last, iv, vol = row[off + 1 : off + 7]
                    records.append(dict(strike=float(strike), side=side,
                                        bid=bid, ask=ask, last=last,
                                        iv=iv, volume=vol))
        emit(meta, records)
    return sorted(chains, key=lambda c: c.days)


def otm_smile(chain: Chain) -> pd.DataFrame:
    """OTM implied vols from quoted IVM: puts below the future, calls above.
    Drops strikes with no two-sided market (bid <= 0)."""
    q = chain.quotes
    otm = q[((q.side == "put") & (q.strike <= chain.future) |
             (q.side == "call") & (q.strike > chain.future))
            & (q.bid > 0) & (q.ask > 0) & (q.iv > 0)]
    return otm.sort_values("strike")[["strike", "iv", "side", "mid"]]


def black76_call(F, K, sigma, T, r=RISK_FREE):
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))


@dataclass
class RND:
    chain: Chain
    grid: np.ndarray      # strike grid
    density: np.ndarray   # risk-neutral pdf over grid

    def cdf(self, x: float) -> float:
        mask = self.grid <= x
        return float(np.trapezoid(self.density[mask], self.grid[mask]))

    def prob_above(self, x: float) -> float:
        return 1.0 - self.cdf(x)

    def quantile(self, p: float) -> float:
        c = np.concatenate([[0], np.cumsum(
            np.diff(self.grid) * 0.5 * (self.density[1:] + self.density[:-1]))])
        c /= c[-1]
        return float(np.interp(p, c, self.grid))

    @property
    def mean(self) -> float:
        return float(np.trapezoid(self.grid * self.density, self.grid))


def fit_rnd(chain: Chain, smooth_factor: float = 1.0, n_grid: int = 2001) -> RND:
    """Breeden-Litzenberger density from the smoothed OTM vol smile.

    The smile is splined in strike space inside the quoted range. Beyond the
    quoted wings the boundary slope decays smoothly to flat,
    vol(K) = v_b + m_b * s * (1 - exp(-(K - k_b)/s)) with s = 15% of the
    future - continuous in level and slope, so the density has no boundary
    kinks, and asymptotically flat, so it neither invents unbounded skew nor
    truncates the tail. Tiny negative density values from differentiation
    noise are clipped and the density renormalized.
    """
    smile = otm_smile(chain)
    k, iv = smile.strike.to_numpy(), smile.iv.to_numpy() / 100.0
    spline = UnivariateSpline(k, iv, s=smooth_factor * len(k) * iv.var())
    lo, hi = chain.future * 0.25, chain.future * 3.0
    grid = np.linspace(lo, hi, n_grid)
    scale = 0.15 * chain.future
    vol = spline(np.clip(grid, k.min(), k.max())).astype(float)
    for kb, outside in ((k.min(), grid < k.min()), (k.max(), grid > k.max())):
        vb, mb = float(spline(kb)), float(spline.derivative()(kb))
        d = np.abs(grid[outside] - kb)
        sign = -1.0 if kb == k.min() else 1.0
        vol[outside] = vb + sign * mb * scale * (1 - np.exp(-d / scale))
    vol = np.clip(vol, 0.01, None)
    calls = black76_call(chain.future, grid, vol, chain.years)
    dens = np.exp(RISK_FREE * chain.years) * np.gradient(
        np.gradient(calls, grid), grid)
    dens = np.clip(dens, 0, None)
    dens /= np.trapezoid(dens, grid)
    return RND(chain=chain, grid=grid, density=dens)


def tail_table(rnds: list[RND], thresholds=(100, 120, 150),
               quantiles=(0.05, 0.50, 0.95, 0.99)) -> pd.DataFrame:
    rows = []
    for r in rnds:
        row = {"expiry": r.chain.label, "days": r.chain.days,
               "future": r.chain.future, "rn_mean": r.mean}
        for t in thresholds:
            row[f"P(>${t})"] = r.prob_above(t)
        for q in quantiles:
            row[f"q{int(q*100):02d}"] = r.quantile(q)
        rows.append(row)
    return pd.DataFrame(rows).set_index("expiry")

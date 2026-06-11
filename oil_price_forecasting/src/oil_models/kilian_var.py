"""Kilian (2009) structural VAR: estimation, identification, IRFs, FEVD,
historical decomposition, wild-bootstrap bands, and forecasting.

Specification (see docs/Kilian_VAR_Build_Guide.md): monthly VAR(24) with a
constant, variables ordered [dprod_pct, real_activity_igrea,
ln_real_oil_price], identified recursively (Cholesky). Sign normalization:
the supply shock is a production *disruption* (negative production impact);
both demand shocks raise the real price on impact.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SHOCK_NAMES = ["oil supply", "aggregate demand", "oil-specific demand"]
DEFAULT_LAGS = 24


@dataclass
class SVAR:
    data: pd.DataFrame            # the estimation sample (T x k), in order
    lags: int
    const: np.ndarray             # (k,)
    coefs: np.ndarray             # (lags, k, k): A_1..A_p
    resid: np.ndarray             # (T-lags, k) reduced-form residuals u_t
    sigma_u: np.ndarray           # (k, k)
    P: np.ndarray                 # sign-normalized Cholesky factor (impact matrix)
    shocks: np.ndarray = field(init=False)  # (T-lags, k) structural shocks (unit variance)

    def __post_init__(self):
        self.shocks = self.resid @ np.linalg.inv(self.P).T

    @property
    def names(self):
        return list(self.data.columns)

    @property
    def k(self):
        return self.data.shape[1]


def fit(data: pd.DataFrame, lags: int = DEFAULT_LAGS) -> SVAR:
    """OLS equation-by-equation VAR with a constant, then Cholesky identification."""
    Y = data.to_numpy(float)
    T, k = Y.shape
    X = np.hstack([np.ones((T - lags, 1))] + [Y[lags - i - 1 : T - i - 1] for i in range(lags)])
    Yt = Y[lags:]
    B, *_ = np.linalg.lstsq(X, Yt, rcond=None)
    resid = Yt - X @ B
    dof = X.shape[0] - X.shape[1]
    sigma_u = resid.T @ resid / dof
    const = B[0]
    coefs = B[1:].reshape(lags, k, k).transpose(0, 2, 1)  # A_i with y_t = c + sum A_i y_{t-i}
    P = _normalize_signs(np.linalg.cholesky(sigma_u))
    return SVAR(data=data, lags=lags, const=const, coefs=coefs,
                resid=resid, sigma_u=sigma_u, P=P)


def _normalize_signs(P: np.ndarray) -> np.ndarray:
    """Supply shock = disruption (negative production impact); demand shocks
    raise the price on impact."""
    signs = np.ones(P.shape[1])
    if P[0, 0] > 0:        # col 0: flip so production falls
        signs[0] = -1
    for j in range(1, P.shape[1]):  # demand shocks: price (last row) rises
        if P[-1, j] < 0:
            signs[j] = -1
    return P * signs


def companion(model: SVAR) -> np.ndarray:
    k, p = model.k, model.lags
    A = np.zeros((k * p, k * p))
    A[:k] = np.hstack(list(model.coefs))
    A[k:, :-k] = np.eye(k * (p - 1))
    return A


def stable(model: SVAR) -> tuple[bool, float]:
    roots = np.abs(np.linalg.eigvals(companion(model)))
    return bool(roots.max() < 1.0), float(roots.max())


def ma_coeffs(model: SVAR, horizon: int) -> np.ndarray:
    """Reduced-form MA matrices Phi_0..Phi_h via recursion."""
    k, p = model.k, model.lags
    phis = np.zeros((horizon + 1, k, k))
    phis[0] = np.eye(k)
    for h in range(1, horizon + 1):
        for i in range(1, min(h, p) + 1):
            phis[h] += model.coefs[i - 1] @ phis[h - i]
    return phis


def irf(model: SVAR, horizon: int = 18) -> np.ndarray:
    """Structural IRFs, shape (horizon+1, k variables, k shocks), to
    one-standard-deviation shocks."""
    return ma_coeffs(model, horizon) @ model.P


def fevd(model: SVAR, horizon: int = 18) -> np.ndarray:
    """Forecast-error variance shares, shape (horizon+1, k variables, k shocks)."""
    theta = irf(model, horizon)
    num = np.cumsum(theta**2, axis=0)
    denom = num.sum(axis=2, keepdims=True)
    return num / denom


def bootstrap_irf(model: SVAR, horizon: int = 18, reps: int = 1000,
                  ci: float = 0.95, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Recursive-design wild bootstrap (Rademacher) percentile bands for the IRFs."""
    rng = np.random.default_rng(seed)
    Y = model.data.to_numpy(float)
    p, k = model.lags, model.k
    Tn = model.resid.shape[0]
    sims = np.empty((reps, horizon + 1, k, k))
    for r in range(reps):
        eta = rng.choice([-1.0, 1.0], size=(Tn, 1))
        u_star = model.resid * eta
        Ys = np.empty_like(Y)
        Ys[:p] = Y[:p]
        for t in range(p, len(Y)):
            yhat = model.const.copy()
            for i in range(p):
                yhat += model.coefs[i] @ Ys[t - i - 1]
            Ys[t] = yhat + u_star[t - p]
        boot = fit(pd.DataFrame(Ys, columns=model.names), lags=p)
        sims[r] = irf(boot, horizon)
    lo = np.quantile(sims, (1 - ci) / 2, axis=0)
    hi = np.quantile(sims, 1 - (1 - ci) / 2, axis=0)
    return lo, hi


def historical_decomposition(model: SVAR) -> dict[str, pd.DataFrame]:
    """Each variable's path split into cumulative contributions of the three
    structural shocks plus a base (initial conditions + deterministic)."""
    theta = irf(model, model.resid.shape[0] - 1)
    e = model.shocks
    Tn, k = e.shape
    contrib = np.zeros((Tn, k, k))  # t, variable, shock
    for t in range(Tn):
        # sum_{i=0..t} Theta_i e_{t-i}
        contrib[t] = np.einsum("ijm,im->jm", theta[: t + 1], e[t::-1])
    idx = model.data.index[model.lags:]
    actual = model.data.iloc[model.lags:]
    out = {}
    for j, name in enumerate(model.names):
        df = pd.DataFrame(contrib[:, j, :], index=idx, columns=SHOCK_NAMES)
        df["base"] = actual[name].to_numpy() - df.sum(axis=1)
        df["actual"] = actual[name].to_numpy()
        out[name] = df
    return out


def forecast(model: SVAR, horizon: int) -> pd.DataFrame:
    """Unconditional point forecast by iterating the VAR forward."""
    Y = model.data.to_numpy(float)
    hist = list(Y[-model.lags:])
    rows = []
    for _ in range(horizon):
        yhat = model.const.copy()
        for i in range(model.lags):
            yhat += model.coefs[i] @ hist[-i - 1]
        rows.append(yhat)
        hist.append(yhat)
    idx = pd.date_range(model.data.index[-1] + pd.offsets.MonthBegin(),
                        periods=horizon, freq="MS")
    return pd.DataFrame(rows, index=idx, columns=model.names)


def scenario_forecast(model: SVAR, shock_path: np.ndarray, horizon: int) -> pd.DataFrame:
    """Conditional forecast: unconditional path plus the effect of a sequence
    of structural shocks.

    shock_path: (m, k) structural shocks (in standard-deviation units) hitting
    in forecast months 1..m.
    """
    base = forecast(model, horizon)
    theta = irf(model, horizon)
    effect = np.zeros((horizon, model.k))
    m = shock_path.shape[0]
    for h in range(horizon):
        for i in range(min(h + 1, m)):
            effect[h] += theta[h - i] @ shock_path[i]
    return base + effect

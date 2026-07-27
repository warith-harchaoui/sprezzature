#!/usr/bin/env python3
"""
market_data — the synthetic dataset behind the financial-markets dashboard.

The strategy is a fully illustrative systematic long-only equity strategy: a
universe of 100 stocks priced daily from 02/01/2024 to 23/07/2026, out of which
the strategy holds an **automatically-sized** basket of the ``K_t`` strongest
names, re-estimated every 25 sessions and free to range from 3 to 40 holdings.
The reference matplotlib overview (``dashboard_dynamic_k_overview.png``) drew the
same idea in six grey panels; this module produces the numbers our house-style
SVG dashboard re-draws far more beautifully.

Nothing here is a real ticker. The universe is a correlated geometric random
walk (one shared market factor plus idiosyncratic noise); the sizing rule, the
fees and the turnover are deterministic functions of that walk. Everything is
reproducible from a single seed so the dashboard is stable across renders.

The module is **numpy-only** — no pandas, no network — so it stays importable in
any environment the ``sprezzature-figures`` tooling already runs in.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np

# --------------------------------------------------------------------------- #
# Simulation constants — the "prospectus" of the illustrative strategy.        #
# --------------------------------------------------------------------------- #
N_ASSETS = 100          # universe size — the "100 actions"
START = date(2024, 1, 2)
END = date(2026, 7, 23)
REBALANCE_EVERY = 25    # sessions between two re-estimations of K_t
K_MIN, K_MAX = 3, 40    # the automatic holding count is clamped to this range
FEE_BPS = 10.0          # round-trip transaction cost, in basis points of turnover
WARMUP = 120            # trailing sessions used to seed the first signal


# --------------------------------------------------------------------------- #
# Calendar                                                                     #
# --------------------------------------------------------------------------- #
def business_days(start: date, end: date) -> List[date]:
    """Return every weekday (Mon–Fri) in ``[start, end]`` inclusive.

    Holidays are intentionally ignored — the dashboard is illustrative and a
    clean five-day week keeps the session index tidy.

    Parameters
    ----------
    start, end : datetime.date
        Inclusive calendar bounds.

    Returns
    -------
    list of datetime.date
        The ordered business days.
    """
    days: List[date] = []
    d = start
    one = timedelta(days=1)
    while d <= end:
        if d.weekday() < 5:  # 0=Mon .. 4=Fri
            days.append(d)
        d += one
    return days


# --------------------------------------------------------------------------- #
# Price universe                                                               #
# --------------------------------------------------------------------------- #
def simulate_universe(n_days: int, seed: int = 7, regime: str = "favorable") -> Dict[str, np.ndarray]:
    """Simulate ``N_ASSETS`` correlated daily log-price paths.

    Each asset return is a blend of one shared **market factor** and an
    idiosyncratic shock, so the cross-section co-moves the way a real index
    would while still fanning out. A handful of assets carry a persistent drift
    (the eventual "winners") so the momentum sizing rule has something to find.

    Parameters
    ----------
    n_days : int
        Number of sessions to simulate.
    seed : int, optional
        Seed for the random generator (reproducible dashboard).

    Returns
    -------
    dict of str to numpy.ndarray
        ``{"prices": (n_days, N_ASSETS), "rets": (n_days, N_ASSETS),
        "logp_z": (n_days, N_ASSETS)}`` — levels, simple daily returns, and the
        centred-reduced log-price used for the faint "100 profiles" panel.
    """
    rng = np.random.default_rng(seed)
    n = n_days
    k = N_ASSETS
    t = np.arange(n)
    market_vol = 0.0072 * (1.0 + 0.45 * np.sin(2 * np.pi * t / 190.0) ** 2)
    beta = rng.uniform(0.6, 1.4, size=k)

    if regime == "adverse":
        # Régime DÉFAVORABLE — celui que la relecture réclamait. Marché légèrement
        # baissier, aucun trenceur persistant, et surtout un RETOUR À LA MOYENNE :
        # les hausses récentes se paient ensuite. Suivre le momentum (acheter les
        # gagnants récents) fait alors entrer juste avant le retournement, et la
        # rotation paie des frais pour rien : la stratégie sous-performe.
        market = rng.normal(-0.00020, 1.0, size=n) * market_vol
        idio_vol = rng.uniform(0.012, 0.028, size=k)
        drift = rng.normal(-0.00005, 0.0006, size=k)
        base = drift[None, :] + beta[None, :] * market[:, None] + rng.normal(0.0, 1.0, size=(n, k)) * idio_vol
        rets = np.empty((n, k))
        win, strength = 60, 0.05
        for i in range(n):
            if i >= win:
                trail = rets[i - win:i].sum(axis=0)               # rendement cumulé récent
                rets[i] = base[i] - strength * trail / win        # tiré vers la moyenne
            else:
                rets[i] = base[i]
    else:
        # Régime FAVORABLE — marché en légère hausse et une poignée de trenceurs
        # persistants que le momentum doit capter ; la stratégie surperforme.
        market = rng.normal(0.00035, 1.0, size=n) * market_vol
        idio_vol = rng.uniform(0.010, 0.024, size=k)
        drift = rng.normal(0.00045, 0.0006, size=k)
        drift[np.argsort(drift)[-14:]] += 0.0016                  # une poignée de forts trenceurs
        rets = drift[None, :] + beta[None, :] * market[:, None] + rng.normal(0.0, 1.0, size=(n, k)) * idio_vol

    # Levels start at 100 and compound; centred-reduced log-price for the profiles.
    prices = 100.0 * np.exp(np.cumsum(rets, axis=0))
    logp = np.log(prices)
    logp_z = (logp - logp.mean(axis=0, keepdims=True)) / (logp.std(axis=0, keepdims=True) + 1e-9)

    return {"prices": prices, "rets": rets, "logp_z": logp_z}


# --------------------------------------------------------------------------- #
# The automatically-sized strategy                                            #
# --------------------------------------------------------------------------- #
def _auto_k(dispersion: float) -> int:
    """Map cross-sectional momentum dispersion to a holding count in [K_MIN, K_MAX].

    The idea the reference chart nods at: when the winners are few and far ahead
    (high dispersion) the strategy **concentrates** into a small basket; when the
    field is bunched (low dispersion) it **spreads** across many names. The map
    is a smooth, clamped inverse of dispersion.

    Parameters
    ----------
    dispersion : float
        Standard deviation of the trailing-momentum signal across the universe.

    Returns
    -------
    int
        The target number of holdings, clamped to ``[K_MIN, K_MAX]``.
    """
    # Invert dispersion onto the [K_MIN, K_MAX] range: when the winners pull far
    # ahead of the pack (high dispersion) the book concentrates into a few large
    # bets; when the field bunches up it spreads wide. The exponent is tuned so a
    # realistic dispersion sweep exercises most of the 3..40 range.
    raw = K_MAX * np.exp(-5.5 * dispersion)
    return int(np.clip(round(raw), K_MIN, K_MAX))


def run_strategy(prices: np.ndarray, rets: np.ndarray) -> Dict[str, np.ndarray]:
    """Run the automatic-``K_t`` momentum strategy over the simulated universe.

    Every ``REBALANCE_EVERY`` sessions the strategy ranks names by trailing
    120-session momentum, picks the top ``K_t`` (chosen by :func:`_auto_k`), and
    holds them equal-weighted until the next rebalance. Turnover at each
    rebalance incurs a ``FEE_BPS`` cost that separates the **gross** and **net**
    equity curves.

    Parameters
    ----------
    prices : numpy.ndarray, shape (n_days, N_ASSETS)
        Price levels.
    rets : numpy.ndarray, shape (n_days, N_ASSETS)
        Simple daily returns.

    Returns
    -------
    dict of str to numpy.ndarray
        Keys: ``k_series`` (n_days,), ``gross_ret`` / ``net_ret`` (n_days,),
        ``wealth_net`` / ``wealth_gross`` (n_days,), ``rebalance_idx`` (m,),
        ``turnover`` (m,), ``fee_event`` (m,), ``fee_cum`` (n_days,).
    """
    n, k = prices.shape
    k_series = np.zeros(n, dtype=int)
    gross_ret = np.zeros(n)
    net_ret = np.zeros(n)
    fee_cum = np.zeros(n)

    weights = np.zeros(k)             # current book, sums to 1 while invested
    rebalance_idx: List[int] = []
    turnover_list: List[float] = []
    fee_event_list: List[float] = []
    cum_fee = 0.0
    cur_k = K_MIN

    for i in range(n):
        # Apply yesterday's book to today's returns (gross of costs).
        g = float(weights @ rets[i]) if weights.any() else 0.0
        gross_ret[i] = g
        cost_today = 0.0

        # Re-estimate on the rebalance grid, once the warm-up window exists.
        if i >= WARMUP and (i - WARMUP) % REBALANCE_EVERY == 0:
            mom = prices[i] / prices[i - WARMUP] - 1.0        # trailing momentum
            disp = float(np.std(mom))
            cur_k = _auto_k(disp)
            winners = np.argsort(mom)[-cur_k:]                # top-K_t names
            new_w = np.zeros(k)
            new_w[winners] = 1.0 / cur_k                      # equal weight
            turn = float(np.abs(new_w - weights).sum())       # L1 turnover
            fee = turn * FEE_BPS / 1e4                         # cost as a return hit
            cost_today = fee
            cum_fee += fee
            rebalance_idx.append(i)
            turnover_list.append(turn)
            fee_event_list.append(fee)
            weights = new_w

        k_series[i] = cur_k if weights.any() else 0
        net_ret[i] = g - cost_today
        fee_cum[i] = cum_fee

    wealth_gross = 100.0 * np.cumprod(1.0 + gross_ret)
    wealth_net = 100.0 * np.cumprod(1.0 + net_ret)

    return {
        "k_series": k_series,
        "gross_ret": gross_ret,
        "net_ret": net_ret,
        "wealth_gross": wealth_gross,
        "wealth_net": wealth_net,
        "rebalance_idx": np.array(rebalance_idx, dtype=int),
        "turnover": np.array(turnover_list),
        "fee_event": np.array(fee_event_list),
        "fee_cum": fee_cum,
    }


def fixed_k_wealth(prices: np.ndarray, rets: np.ndarray, k_hold: int) -> np.ndarray:
    """Return the net wealth curve of a fixed-``k_hold`` variant of the strategy.

    Same momentum ranking and rebalance grid as :func:`run_strategy`, but the
    holding count is pinned to ``k_hold`` rather than chosen automatically. Used
    for the "net wealth compared" panel (K=1..5 alongside the automatic book).

    Parameters
    ----------
    prices, rets : numpy.ndarray
        Price levels and daily returns, shape ``(n_days, N_ASSETS)``.
    k_hold : int
        The fixed number of holdings.

    Returns
    -------
    numpy.ndarray, shape (n_days,)
        The net wealth curve, starting at 100.
    """
    n, k = prices.shape
    weights = np.zeros(k)
    net = np.zeros(n)
    for i in range(n):
        g = float(weights @ rets[i]) if weights.any() else 0.0
        cost = 0.0
        if i >= WARMUP and (i - WARMUP) % REBALANCE_EVERY == 0:
            mom = prices[i] / prices[i - WARMUP] - 1.0
            winners = np.argsort(mom)[-k_hold:]
            new_w = np.zeros(k)
            new_w[winners] = 1.0 / k_hold
            cost = float(np.abs(new_w - weights).sum()) * FEE_BPS / 1e4
            weights = new_w
        net[i] = g - cost
    return 100.0 * np.cumprod(1.0 + net)


# --------------------------------------------------------------------------- #
# Roll-ups for the distribution / calendar panels                             #
# --------------------------------------------------------------------------- #
def monthly_returns(days: List[date], net_ret: np.ndarray) -> Dict[str, object]:
    """Aggregate daily net returns into a (year × month) percentage grid.

    Parameters
    ----------
    days : list of datetime.date
        The session calendar, aligned with ``net_ret``.
    net_ret : numpy.ndarray
        Daily net returns.

    Returns
    -------
    dict
        ``{"years": [2024, ...], "grid": np.ndarray (n_years, 12)}`` — each cell
        the compounded monthly return in percent, ``nan`` where a month has no
        session (before the start / after the end).
    """
    years = sorted({d.year for d in days})
    grid = np.full((len(years), 12), np.nan)
    acc: Dict[Tuple[int, int], float] = {}
    for d, r in zip(days, net_ret):
        key = (d.year, d.month)
        acc[key] = (1.0 + acc.get(key, 0.0)) * (1.0 + r) - 1.0
    for (yr, mo), v in acc.items():
        grid[years.index(yr), mo - 1] = v * 100.0
    return {"years": years, "grid": grid}


def drawdown(wealth: np.ndarray) -> np.ndarray:
    """Return the running drawdown of a wealth curve, in percent (<= 0).

    Parameters
    ----------
    wealth : numpy.ndarray
        A wealth/equity curve.

    Returns
    -------
    numpy.ndarray
        ``(wealth / running_peak - 1) * 100`` — zero at new highs, negative in
        every trough.
    """
    peak = np.maximum.accumulate(wealth)
    return (wealth / peak - 1.0) * 100.0


# --------------------------------------------------------------------------- #
# Public assembly                                                             #
# --------------------------------------------------------------------------- #
@dataclass
class Portfolio:
    """Everything the dashboard panels need, computed once and passed around."""

    days: List[date]
    prices: np.ndarray
    rets: np.ndarray
    logp_z: np.ndarray
    k_series: np.ndarray
    gross_ret: np.ndarray
    net_ret: np.ndarray
    wealth_gross: np.ndarray
    wealth_net: np.ndarray
    rebalance_idx: np.ndarray
    turnover: np.ndarray
    fee_event: np.ndarray
    fee_cum: np.ndarray
    fixed_wealth: Dict[int, np.ndarray]
    buyhold: np.ndarray
    monthly: Dict[str, object]
    dd: np.ndarray


def build(seed: int = 48, regime: str = "favorable") -> Portfolio:
    """Build the full illustrative dataset for the dashboard.

    Parameters
    ----------
    seed : int, optional
        Master seed threaded into the universe simulation.

    Returns
    -------
    Portfolio
        A populated record ready to hand to the panel renderers.
    """
    days = business_days(START, END)
    n = len(days)
    uni = simulate_universe(n, seed=seed, regime=regime)
    prices, rets, logp_z = uni["prices"], uni["rets"], uni["logp_z"]

    strat = run_strategy(prices, rets)
    fixed = {kk: fixed_k_wealth(prices, rets, kk) for kk in (1, 2, 3, 4, 5)}
    # Buy-and-hold the whole universe, equal-weighted from day one.
    buyhold = 100.0 * np.cumprod(1.0 + rets.mean(axis=1))

    return Portfolio(
        days=days,
        prices=prices,
        rets=rets,
        logp_z=logp_z,
        k_series=strat["k_series"],
        gross_ret=strat["gross_ret"],
        net_ret=strat["net_ret"],
        wealth_gross=strat["wealth_gross"],
        wealth_net=strat["wealth_net"],
        rebalance_idx=strat["rebalance_idx"],
        turnover=strat["turnover"],
        fee_event=strat["fee_event"],
        fee_cum=strat["fee_cum"],
        fixed_wealth=fixed,
        buyhold=buyhold,
        monthly=monthly_returns(days, strat["net_ret"]),
        dd=drawdown(strat["wealth_net"]),
    )


if __name__ == "__main__":
    g = build()
    print(f"sessions      : {len(g.days)}  ({g.days[0]} → {g.days[-1]})")
    print(f"rebalances    : {len(g.rebalance_idx)}")
    print(f"K_t range     : {g.k_series[g.k_series > 0].min()}–{g.k_series.max()}")
    print(f"net wealth end: {g.wealth_net[-1]:.1f}   gross: {g.wealth_gross[-1]:.1f}")
    print(f"buy&hold end  : {g.buyhold[-1]:.1f}")
    print(f"cum fees end  : {g.fee_cum[-1]*100:.2f}% of NAV")
    print(f"max drawdown  : {g.dd.min():.1f}%")
    print(f"months        : {g.monthly['grid'].shape}")

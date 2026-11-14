#!/usr/bin/env python3
"""btc-cent-forecast-01: 4-hour-ahead Bitcoin point forecast.

For each case the program reads the case's own 72 hours of 1-minute
closes and returns one number: the price it expects 240 minutes after
the checkpoint. The score is mean absolute error, so the right point
forecast is the conditional median of the 240-minute change, and that
is what this estimates from the case's own window.

Method, per case:
    guess = last_close * exp(centre + pullback)
where `centre` is the 45th percentile of the overlapping 240-minute
log-returns inside the window, and `pullback` is a mean-reversion
correction split over two horizons: -0.20 times the most recent
240-minute log-return and -0.05 times the most recent 120-minute
log-return. Four-hour Bitcoin returns are negatively autocorrelated
(AR(1) slope near -0.35 on the practice history), so after a large
move the price tends to give part of it back in the next four hours;
the 2-hour leg carries a small share of the same signal. The total
correction is capped at +/-5% so one extreme move can never dominate
the forecast.

Everything is estimated from the case's own window, so the forecast
adapts to the final's own regime. Nothing is fitted to the practice
answers: the last practice case's actual is not in the kit.

Local backtest (reconstructed from the six practice cases, whose
targets are the next case's checkpoint close): on the five practice
cases with known actuals this scores 44,470 cents mean absolute
error against 47,055 for the persistence baseline (-5.5%); on a
12-point sub-checkpoint evaluation inside the same windows it scores
37,657 against 38,110 (-1.2%). The official six-case persistence
baseline is 44,521.577 cents (measured by the house).

Standard library only, offline, deterministic: no randomness, no
network, no clock. Reads every *.in in the input directory
(MAKEFUN_INPUT_DIR or /input) in name order and writes one *.out
per case to MAKEFUN_OUTPUT_DIR or /output.
"""

import json
import math
import os
from pathlib import Path

LOWEST_PRICE = 0.00001
HIGHEST_PRICE = 9_999_999.99999
LONG_HORIZON = 240
SHORT_HORIZON = 120
LONG_WEIGHT = 0.20
SHORT_WEIGHT = 0.05
MOVE_CAP = 0.05


def snap(x):
    """Keep a price on the scorer's grid: 5 decimals, inside (0, 10e6)."""
    clipped = min(HIGHEST_PRICE, max(LOWEST_PRICE, x))
    return round(clipped * 1e5) / 1e5


def pct(sorted_values, q):
    """Linear-interpolated q-quantile of an already sorted list."""
    if not sorted_values:
        return 0.0
    spot = q * (len(sorted_values) - 1)
    below = int(spot)
    above = min(below + 1, len(sorted_values) - 1)
    part = spot - below
    return sorted_values[below] * (1.0 - part) + sorted_values[above] * part


def log_change(prices, lag):
    """Log-return of the last price against the price `lag` minutes back."""
    older = prices[-lag - 1]
    return math.log(prices[-1] / older) if older > 0 else 0.0


def guess_price(prices):
    """One 240-minute-ahead price guess from a list of 1-minute closes."""
    if not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not math.isfinite(last) or last <= 0:
        raise ValueError("last price is not a finite positive number")
    if len(prices) <= LONG_HORIZON:
        # Too little history to estimate a change distribution: persistence.
        return snap(last)
    moves = [math.log(prices[i] / prices[i - LONG_HORIZON])
             for i in range(LONG_HORIZON, len(prices))
             if prices[i - LONG_HORIZON] > 0 and prices[i] > 0]
    if not moves:
        return snap(last)
    moves.sort()
    centre = pct(moves, 0.45)
    # Mean reversion over two horizons; the cap never binds on the
    # practice history (largest |move| there is about 0.02), it only
    # guards the final against one extreme 4-hour swing.
    pullback = (-LONG_WEIGHT * log_change(prices, LONG_HORIZON)
                - SHORT_WEIGHT * log_change(prices, SHORT_HORIZON))
    shift = max(-MOVE_CAP, min(MOVE_CAP, centre + pullback))
    return snap(last * math.exp(shift))


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for p in input_dir.iterdir()
                    if p.is_file() and p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        case = json.loads(path.read_text(encoding="utf-8"))
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        guess = guess_price(markets[0]["prices"])
        payload = {"forecasts": [{"case": case_id, "price": guess}]}
        (output_dir / f"{case_id}.out").write_text(
            json.dumps(payload) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

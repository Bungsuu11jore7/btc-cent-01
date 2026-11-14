# Bitcoin 4h Forecast — Two-Horizon Median-Reversion Forecaster

Entry for make.fun `btc-cent-forecast-01`: forecast Bitcoin's US-dollar
price 240 minutes after each checkpoint, 12 times over 48 hours. Score is
the mean absolute error in cents; lower is better, and a prize needs a
score strictly below the house persistence baseline.

## Method

One program, `main.py` (Python 3.13, standard library only, offline,
deterministic). For each case it reads the case's own 72 hours of
1-minute closes and forecasts:

    forecast = last_close * exp(q45 - 0.20 * r240 - 0.05 * r120)

- `q45` is the 45th percentile of the overlapping 240-minute log-returns
  in the case window — the robust centre of the recent 4-hour change
  distribution.
- `r240` and `r120` are the most recent 240- and 120-minute log-returns.
  Their coefficients are negative because Bitcoin returns are negatively
  autocorrelated (AR(1) slope about -0.35 on the practice history): after
  a large move the price tends to give part of it back in the next four
  hours. The total reversal weight (0.25) is split across the two
  horizons so the 2-hour leg carries a small share of the same signal.
- The combined shift is capped at +/-5% so one extreme move can never
  dominate the forecast.

The score is mean absolute error, so the best point forecast is the
conditional median of the 4-hour change — that is what this estimates.
Both terms are computed from the case's own window, so the forecast
adapts to the final's own regime. Nothing is fitted to the practice
answers (the last practice case's actual is not in the kit at all).

## Local backtest

Reconstructed from the six practice cases: each case's target is the next
case's checkpoint close, so five cases (p00–p04) have known actuals.
A second, 12-point evaluation uses sub-checkpoints 24 h and 48 h into
each case's own window, with targets still inside that window.

| method | 5-case MAE (cents) | 12-point MAE (cents) |
|---|---|---|
| persistence (house baseline) | 47,055 | 38,110 |
| this forecaster | 44,470 (-5.5%) | 37,657 (-1.2%) |

The house's official six-case persistence baseline is 44,521.577 cents;
the final is scored on unseen prices, so no practice number guarantees
a final result.

## Running it

    mkdir -p out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py

Reads every `*.in` in the input directory in name order and writes one
`*.out` per case: `{"forecasts": [{"case": "<id>", "price": <number>}]}`.
Runs in well under a second per case; two runs are byte-identical.

# agent/tools/drift_detection_engine.py

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WINDOW_SIZE = 24    # months per rolling window
STEP_SIZE = 1       # months to step forward each iteration
DRIFT_THRESHOLD = 1.5  # standard deviations to flag drift


class DriftEvent(BaseModel):
    date: str           # "YYYY-MM" - the end date of the window where drift was flagged
    factor: str         # which factor drifted
    loading: float      # the loading in this window
    historical_mean: float   # mean of all prior windows for this factor
    historical_std: float    # std of all prior windows for this factor
    z_score: float      # how many std devs away from historical mean
    direction: str      # "increase" or "decrease"


class RollingWindow(BaseModel):
    date: str           # "YYYY-MM" - end date of this window
    factor_loadings: dict   # {factor_name: loading}
    adj_r_squared: float
    num_observations: int


class DriftDetectionInput(BaseModel):
    ticker: str
    returns: dict       # {"YYYY-MM": float} - from FundPriceOutput.returns
    factors: dict       # {"YYYY-MM": {factor: value}} - from FrenchFactorOutput.factors
    start_date: str     # "YYYY-MM"
    end_date: str       # "YYYY-MM"
    window_size: int = WINDOW_SIZE
    drift_threshold: float = DRIFT_THRESHOLD


class DriftDetectionOutput(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    num_windows: int
    window_size: int
    rolling_windows: list[RollingWindow]   # one entry per window
    drift_events: list[DriftEvent]         # one entry per flagged drift
    factors_analyzed: list[str]
    source: str
    error: Optional[str] = None


def _align_data(returns: dict, factors: dict) -> pd.DataFrame:
    """
    Convert input dicts to a single aligned DataFrame.
    Same alignment logic as the regression engine.
    """
    returns_s = pd.Series(returns, name="fund_return")
    returns_s.index = pd.to_datetime(returns_s.index, format="%Y-%m")
    returns_s.index = returns_s.index.to_period("M").to_timestamp("M")

    factors_df = pd.DataFrame.from_dict(factors, orient="index")
    factors_df.index = pd.to_datetime(factors_df.index, format="%Y-%m")
    factors_df.index = factors_df.index.to_period("M").to_timestamp("M")
    factors_df.columns = factors_df.columns.str.strip()

    aligned = returns_s.to_frame().join(factors_df, how="inner")
    return aligned


def _run_single_ols(window_data: pd.DataFrame) -> tuple[dict, float]:
    """
    Run OLS on a single window slice.
    Returns (factor_loadings dict, adj_r_squared).
    """
    factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]

    y = window_data["fund_return"] - window_data["RF"]
    X = window_data[factor_cols]
    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    loadings = {f: round(float(model.params[f]), 6) for f in factor_cols}
    adj_r2 = round(float(model.rsquared_adj), 4)

    return loadings, adj_r2


def detect_drift(inp: DriftDetectionInput) -> DriftDetectionOutput:
    try:
        factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]

        # Align data
        aligned = _align_data(inp.returns, inp.factors)

        # Filter to requested date range
        start = pd.to_datetime(inp.start_date, format="%Y-%m").to_period("M").to_timestamp("M")
        end = pd.to_datetime(inp.end_date, format="%Y-%m").to_period("M").to_timestamp("M")
        aligned = aligned.loc[start:end]

        n_total = len(aligned)

        if n_total < inp.window_size:
            raise ValueError(
                f"Not enough data for rolling window. "
                f"Need {inp.window_size} months, have {n_total}."
            )

        # Rolling window regression
        rolling_windows = []
        all_loadings = {f: [] for f in factor_cols}  # track history per factor

        n_windows = n_total - inp.window_size + 1

        for i in range(n_windows):
            window = aligned.iloc[i: i + inp.window_size]
            window_end = window.index[-1].strftime("%Y-%m")

            loadings, adj_r2 = _run_single_ols(window)

            rolling_windows.append(RollingWindow(
                date=window_end,
                factor_loadings=loadings,
                adj_r_squared=adj_r2,
                num_observations=len(window)
            ))

            # Accumulate loadings history
            for f in factor_cols:
                all_loadings[f].append(loadings[f])

        # Drift detection
        # For each window (after the first few to have enough history),
        # compare current loading against mean/std of all prior windows.
        # Minimum 12 prior windows before flagging drift (avoid false positives early on).
        drift_events = []
        MIN_HISTORY = 12

        for i, rw in enumerate(rolling_windows):
            if i < MIN_HISTORY:
                continue  # not enough history yet

            for f in factor_cols:
                prior_loadings = all_loadings[f][:i]  # all windows before this one
                hist_mean = float(np.mean(prior_loadings))
                hist_std = float(np.std(prior_loadings))

                if hist_std < 1e-6:
                    continue  # avoid division by zero if std is negligible

                current_loading = rw.factor_loadings[f]
                z_score = (current_loading - hist_mean) / hist_std

                if abs(z_score) >= inp.drift_threshold:
                    drift_events.append(DriftEvent(
                        date=rw.date,
                        factor=f,
                        loading=round(current_loading, 6),
                        historical_mean=round(hist_mean, 6),
                        historical_std=round(hist_std, 6),
                        z_score=round(z_score, 4),
                        direction="increase" if z_score > 0 else "decrease"
                    ))

        return DriftDetectionOutput(
            ticker=inp.ticker,
            start_date=aligned.index[0].strftime("%Y-%m"),
            end_date=aligned.index[-1].strftime("%Y-%m"),
            num_windows=len(rolling_windows),
            window_size=inp.window_size,
            rolling_windows=rolling_windows,
            drift_events=drift_events,
            factors_analyzed=factor_cols,
            source="Rolling OLS regression via statsmodels. Factors: Ken French Data Library.",
            error=None
        )

    except Exception as e:
        return DriftDetectionOutput(
            ticker=inp.ticker,
            start_date=inp.start_date,
            end_date=inp.end_date,
            num_windows=0,
            window_size=inp.window_size,
            rolling_windows=[],
            drift_events=[],
            factors_analyzed=[],
            source="Rolling OLS regression via statsmodels",
            error=str(e)
        )


if __name__ == "__main__":
    from agent.tools.french_factor_fetcher import get_french_factors, FrenchFactorInput
    from agent.tools.fund_price_fetcher import get_fund_returns, FundPriceInput

    # Fetch inputs
    factors = get_french_factors(FrenchFactorInput(
        start_date="2019-01",
        end_date="2025-12"
    ))
    prices = get_fund_returns(FundPriceInput(
        ticker="ARKK",
        start_date="2019-01",
        end_date="2025-12"
    ))

    # Run drift detection
    result = detect_drift(DriftDetectionInput(
        ticker="ARKK",
        returns=prices.returns,
        factors=factors.factors,
        start_date="2019-01",
        end_date="2025-12"
    ))

    print(f"Ticker: {result.ticker}")
    print(f"Error: {result.error}")
    print(f"Windows computed: {result.num_windows}")
    print(f"Drift events detected: {len(result.drift_events)}")

    if result.drift_events:
        print("\nDrift events:")
        for e in result.drift_events[:5]:  # show first 5
            print(f"  {e.date} | {e.factor} | loading={e.loading:.4f} | "
                  f"z={e.z_score:.2f} | {e.direction}")

    print("\nFirst 3 rolling windows:")
    for w in result.rolling_windows[:3]:
        print(f"  {w.date} | adj_r2={w.adj_r_squared} | "
              f"Mkt-RF={w.factor_loadings['Mkt-RF']:.4f} | "
              f"HML={w.factor_loadings['HML']:.4f}")

    print("\nLast 3 rolling windows:")
    for w in result.rolling_windows[-3:]:
        print(f"  {w.date} | adj_r2={w.adj_r_squared} | "
              f"Mkt-RF={w.factor_loadings['Mkt-RF']:.4f} | "
              f"HML={w.factor_loadings['HML']:.4f}")
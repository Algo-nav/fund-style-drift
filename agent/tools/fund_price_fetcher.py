# agent/tools/fund_price_fetcher.py

import yfinance as yf
import pandas as pd
from pydantic import BaseModel
from typing import Optional


class FundPriceInput(BaseModel):
    ticker: str          # e.g. "QQQ"
    start_date: str      # "YYYY-MM"
    end_date: str        # "YYYY-MM"


class FundPriceOutput(BaseModel):
    ticker: str
    returns: dict        # {"YYYY-MM": float} - monthly returns as decimals
    start_date: str      # actual start date of return series (one month after price start)
    end_date: str        # actual end date of return series
    num_observations: int
    missing_months: int  # number of months with no price data in the requested range
    source: str
    error: Optional[str] = None


def get_fund_returns(inp: FundPriceInput) -> FundPriceOutput:
    try:
        # Add one month buffer before start_date to allow pct_change()
        # to produce a return for the first requested month.
        # e.g. if start_date is "2019-01", we pull prices from "2018-12"
        # so the first return computed is for 2019-01.
        start_dt = pd.to_datetime(inp.start_date, format="%Y-%m") - pd.DateOffset(months=1)
        end_dt = pd.to_datetime(inp.end_date, format="%Y-%m") + pd.DateOffset(months=1)

        raw = yf.download(
            inp.ticker,
            start=start_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            interval="1mo",
            auto_adjust=True,
            progress=False
        )

        if raw.empty:
            return FundPriceOutput(
                ticker=inp.ticker,
                returns={},
                start_date=inp.start_date,
                end_date=inp.end_date,
                num_observations=0,
                missing_months=0,
                source="Yahoo Finance via yfinance",
                error=f"No data returned for ticker {inp.ticker}"
            )

        # Pull close prices and normalize index to month-end
        prices = raw["Close"].squeeze()
        prices.index = prices.index.to_period("M").to_timestamp("M")

        # Compute monthly returns
        returns = prices.pct_change().dropna()

        # Filter to requested date range
        start_filter = pd.to_datetime(inp.start_date, format="%Y-%m").to_period("M").to_timestamp("M")
        end_filter = pd.to_datetime(inp.end_date, format="%Y-%m").to_period("M").to_timestamp("M")
        returns = returns.loc[start_filter:end_filter]

        # Check for missing months in the requested range
        expected_months = pd.date_range(
            start=start_filter,
            end=end_filter,
            freq="ME"
        )
        missing_months = len(expected_months) - len(returns)

        # Convert to JSON-serializable dict
        returns_dict = {
            date.strftime("%Y-%m"): round(float(val), 6)
            for date, val in returns.items()
        }

        return FundPriceOutput(
            ticker=inp.ticker,
            returns=returns_dict,
            start_date=returns.index[0].strftime("%Y-%m"),
            end_date=returns.index[-1].strftime("%Y-%m"),
            num_observations=len(returns),
            missing_months=missing_months,
            source="Yahoo Finance via yfinance",
            error=None
        )

    except Exception as e:
        return FundPriceOutput(
            ticker=inp.ticker,
            returns={},
            start_date=inp.start_date,
            end_date=inp.end_date,
            num_observations=0,
            missing_months=0,
            source="Yahoo Finance via yfinance",
            error=str(e)
        )


if __name__ == "__main__":
    # Test with QQQ - we already know what to expect from the notebook
    result = get_fund_returns(FundPriceInput(
        ticker="QQQ",
        start_date="2019-01",
        end_date="2024-12"
    ))
    print(f"Ticker: {result.ticker}")
    print(f"Error: {result.error}")
    print(f"Observations: {result.num_observations}")
    print(f"Missing months: {result.missing_months}")
    print(f"Date range: {result.start_date} to {result.end_date}")
    print("First 3 months:")
    for i, (date, ret) in enumerate(result.returns.items()):
        print(f"  {date}: {ret:.4f}")
        if i >= 2:
            break
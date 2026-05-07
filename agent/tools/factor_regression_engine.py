# agent/tools/factor_regression_engine.py

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ConfidenceDimension(BaseModel):
    label: str        # "high" / "moderate" / "low" / "pass" / "flag" / "adequate" / "marginal" / "insufficient"
    metric: float     # the underlying number
    metric_name: str  # what the number is


class FactorRegressionInput(BaseModel):
    ticker: str
    returns: dict     # {"YYYY-MM": float} - from FundPriceOutput.returns
    factors: dict     # {"YYYY-MM": {factor: value}} - from FrenchFactorOutput.factors
    start_date: str   # "YYYY-MM"
    end_date: str     # "YYYY-MM"


class FactorRegressionOutput(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    num_observations: int

    # Regression results
    alpha: float
    alpha_tstat: float
    alpha_pvalue: float
    factor_loadings: dict   # {factor_name: loading}
    factor_tstats: dict     # {factor_name: t_stat}
    factor_pvalues: dict    # {factor_name: p_value}
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_pvalue: float

    # Confidence dimensions - never collapsed into a single score
    conf_fit: ConfidenceDimension
    conf_significance: ConfidenceDimension
    conf_sample: ConfidenceDimension
    conf_normality: ConfidenceDimension

    source: str
    error: Optional[str] = None


def _label_fit(adj_r2: float) -> str:
    if adj_r2 >= 0.70:
        return "high"
    elif adj_r2 >= 0.40:
        return "moderate"
    return "low"


def _label_significance(sig_count: int) -> str:
    if sig_count >= 4:
        return "high"
    elif sig_count >= 2:
        return "moderate"
    return "low"


def _label_sample(n: int) -> str:
    if n >= 36:
        return "adequate"
    elif n >= 24:
        return "marginal"
    return "insufficient"


def _label_normality(jb_pvalue: float) -> str:
    return "pass" if jb_pvalue >= 0.05 else "flag"


def run_factor_regression(inp: FactorRegressionInput) -> FactorRegressionOutput:
    try:
        # Convert dicts to DataFrames
        returns_df = pd.Series(inp.returns, name="fund_return")
        returns_df.index = pd.to_datetime(returns_df.index, format="%Y-%m")
        returns_df.index = returns_df.index.to_period("M").to_timestamp("M")

        # Build factors DataFrame from nested dict
        factors_df = pd.DataFrame.from_dict(inp.factors, orient="index")
        factors_df.index = pd.to_datetime(factors_df.index, format="%Y-%m")
        factors_df.index = factors_df.index.to_period("M").to_timestamp("M")
        factors_df.columns = factors_df.columns.str.strip()

        # Align on date index
        aligned = returns_df.to_frame().join(factors_df, how="inner")

        # Filter to requested date range
        start = pd.to_datetime(inp.start_date, format="%Y-%m").to_period("M").to_timestamp("M")
        end = pd.to_datetime(inp.end_date, format="%Y-%m").to_period("M").to_timestamp("M")
        aligned = aligned.loc[start:end]

        n = len(aligned)

        # Compute excess returns: fund return minus risk-free rate
        y = aligned["fund_return"] - aligned["RF"]

        # Independent variables: the six factors
        factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
        X = aligned[factor_cols]
        X = sm.add_constant(X)

        # Run OLS
        model = sm.OLS(y, X).fit()

        # Extract results
        alpha = float(model.params["const"])
        alpha_tstat = float(model.tvalues["const"])
        alpha_pvalue = float(model.pvalues["const"])

        factor_loadings = {f: round(float(model.params[f]), 6) for f in factor_cols}
        factor_tstats = {f: round(float(model.tvalues[f]), 4) for f in factor_cols}
        factor_pvalues = {f: round(float(model.pvalues[f]), 4) for f in factor_cols}

        r_squared = round(float(model.rsquared), 4)
        adj_r_squared = round(float(model.rsquared_adj), 4)
        f_statistic = round(float(model.fvalue), 4)
        f_pvalue = round(float(model.f_pvalue), 6)

        # Confidence dimension 1: fit
        conf_fit = ConfidenceDimension(
            label=_label_fit(adj_r_squared),
            metric=adj_r_squared,
            metric_name="adj_r_squared"
        )

        # Confidence dimension 2: factor significance
        sig_count = sum(1 for f in factor_cols if abs(factor_tstats[f]) >= 2.0)
        conf_significance = ConfidenceDimension(
            label=_label_significance(sig_count),
            metric=float(sig_count),
            metric_name="significant_factors"
        )

        # Confidence dimension 3: sample adequacy
        conf_sample = ConfidenceDimension(
            label=_label_sample(n),
            metric=float(n),
            metric_name="num_observations"
        )

        # Confidence dimension 4: residual normality (Jarque-Bera)
        jb_stat, jb_pvalue = stats.jarque_bera(model.resid)
        conf_normality = ConfidenceDimension(
            label=_label_normality(float(jb_pvalue)),
            metric=round(float(jb_pvalue), 4),
            metric_name="jarque_bera_pvalue"
        )

        return FactorRegressionOutput(
            ticker=inp.ticker,
            start_date=aligned.index[0].strftime("%Y-%m"),
            end_date=aligned.index[-1].strftime("%Y-%m"),
            num_observations=n,
            alpha=round(alpha, 6),
            alpha_tstat=round(alpha_tstat, 4),
            alpha_pvalue=round(alpha_pvalue, 4),
            factor_loadings=factor_loadings,
            factor_tstats=factor_tstats,
            factor_pvalues=factor_pvalues,
            r_squared=r_squared,
            adj_r_squared=adj_r_squared,
            f_statistic=f_statistic,
            f_pvalue=f_pvalue,
            conf_fit=conf_fit,
            conf_significance=conf_significance,
            conf_sample=conf_sample,
            conf_normality=conf_normality,
            source="OLS regression via statsmodels. Factors: Ken French Data Library.",
            error=None
        )

    except Exception as e:
        # Return a shell output with error rather than crashing
        dummy_dim = ConfidenceDimension(label="low", metric=0.0, metric_name="n/a")
        return FactorRegressionOutput(
            ticker=inp.ticker,
            start_date=inp.start_date,
            end_date=inp.end_date,
            num_observations=0,
            alpha=0.0, alpha_tstat=0.0, alpha_pvalue=0.0,
            factor_loadings={}, factor_tstats={}, factor_pvalues={},
            r_squared=0.0, adj_r_squared=0.0,
            f_statistic=0.0, f_pvalue=0.0,
            conf_fit=dummy_dim, conf_significance=dummy_dim,
            conf_sample=dummy_dim, conf_normality=dummy_dim,
            source="OLS regression via statsmodels",
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
        ticker="QQQ",
        start_date="2019-01",
        end_date="2025-12"
    ))

    # Run regression
    result = run_factor_regression(FactorRegressionInput(
        ticker="QQQ",
        returns=prices.returns,
        factors=factors.factors,
        start_date="2019-01",
        end_date="2025-12"
    ))

    print(f"Ticker: {result.ticker}")
    print(f"Error: {result.error}")
    print(f"Observations: {result.num_observations}")
    print(f"Alpha: {result.alpha} (t={result.alpha_tstat}, p={result.alpha_pvalue})")
    print(f"R-squared: {result.r_squared}, Adj R-squared: {result.adj_r_squared}")
    print(f"\nFactor loadings:")
    for f, loading in result.factor_loadings.items():
        tstat = result.factor_tstats[f]
        sig = "*" if abs(tstat) >= 2.0 else ""
        print(f"  {f}: {loading:.4f} (t={tstat}){sig}")
    print(f"\nConfidence dimensions:")
    print(f"  Fit:          {result.conf_fit.label} (adj_r2={result.conf_fit.metric})")
    print(f"  Significance: {result.conf_significance.label} ({int(result.conf_significance.metric)}/6 factors significant)")
    print(f"  Sample:       {result.conf_sample.label} ({int(result.conf_sample.metric)} observations)")
    print(f"  Normality:    {result.conf_normality.label} (JB p-value={result.conf_normality.metric})")
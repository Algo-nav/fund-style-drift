# agent/agent.py

import os
import json
import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

from agent.tools.french_factor_fetcher import get_french_factors, FrenchFactorInput
from agent.tools.fund_price_fetcher import get_fund_returns, FundPriceInput
from agent.tools.factor_regression_engine import run_factor_regression, FactorRegressionInput
from agent.tools.drift_detection_engine import detect_drift, DriftDetectionInput
from agent.tools.nport_parser import parse_nport, NportInput
from agent.tools.fund_metadata_fetcher import get_fund_metadata, FundMetadataInput
from agent.tools.chart_generator import generate_charts, ChartInput
from prompts.style_drift import SYSTEM_PROMPT

load_dotenv()

client = Anthropic()

START_DATE = "2019-01"
END_DATE = "2025-12"

def run_agent(ticker: str) -> dict:
    """
    Orchestrates the full fund style drift analysis pipeline for a single ticker.
    Returns a dict with all report components.
    """
    ticker = ticker.upper().strip()
    print(f"\n{'='*60}")
    print(f"Running style drift analysis for {ticker}")
    print(f"{'='*60}")

    report = {
        "ticker": ticker,
        "error": None,
        "metadata": None,
        "regression": None,
        "drift": None,
        "holdings": None,
        "charts": None,
        "narrative": None,
    }

    # Step 1: Fund metadata
    print(f"[1/7] Fetching metadata...")
    metadata = get_fund_metadata(FundMetadataInput(ticker=ticker))
    if metadata.error and not metadata.name:
        print(f"  Warning: {metadata.error}")
    report["metadata"] = metadata.model_dump()
    print(f"  Fund: {metadata.name}")

    # Step 2: Factor data
    print(f"[2/7] Fetching FF6 factor data...")
    factors = get_french_factors(FrenchFactorInput(
        start_date=START_DATE,
        end_date=END_DATE
    ))
    if factors.error:
        report["error"] = f"Factor data failed: {factors.error}"
        return report
    print(f"  Observations: {factors.num_observations}, cache_used: {factors.cache_used}")

    # Step 3: Fund price/NAV data
    print(f"[3/7] Fetching fund returns...")
    prices = get_fund_returns(FundPriceInput(
        ticker=ticker,
        start_date=START_DATE,
        end_date=END_DATE
    ))
    if prices.error:
        report["error"] = f"Price data failed: {prices.error}"
        return report
    print(f"  Observations: {prices.num_observations}, missing: {prices.missing_months}")

    # Step 4: Full-period factor regression
    print(f"[4/7] Running factor regression...")
    regression = run_factor_regression(FactorRegressionInput(
        ticker=ticker,
        returns=prices.returns,
        factors=factors.factors,
        start_date=START_DATE,
        end_date=END_DATE
    ))
    if regression.error:
        report["error"] = f"Regression failed: {regression.error}"
        return report
    print(f"  Adj R²: {regression.adj_r_squared}, Alpha: {regression.alpha:.4f}")
    report["regression"] = regression.model_dump()

    # Step 5: Drift detection
    print(f"[5/7] Running drift detection...")
    drift = detect_drift(DriftDetectionInput(
        ticker=ticker,
        returns=prices.returns,
        factors=factors.factors,
        start_date=START_DATE,
        end_date=END_DATE
    ))
    if drift.error:
        report["error"] = f"Drift detection failed: {drift.error}"
        return report
    print(f"  Windows: {drift.num_windows}, Drift events: {len(drift.drift_events)}")
    report["drift"] = {
        "num_windows": drift.num_windows,
        "drift_events": [e.model_dump() for e in drift.drift_events],
        "rolling_windows": [w.model_dump() for w in drift.rolling_windows],
    }

    # Step 6: N-PORT holdings (best-effort, non-blocking)
    print(f"[6/7] Fetching N-PORT holdings...")
    holdings = parse_nport(NportInput(ticker=ticker, max_holdings=10))
    if holdings.error:
        print(f"  Warning: {holdings.error} (continuing without holdings)")
    else:
        print(f"  Holdings: {holdings.total_holdings}, top 10 concentration: {holdings.top10_concentration}%")
    report["holdings"] = holdings.model_dump()

    # Build cumulative return index (base 100) for NAV chart
    # More comparable across funds than raw prices
    
    returns_series = pd.Series(prices.returns)
    cumulative = (1 + returns_series).cumprod() * 100
    monthly_prices_for_chart = {k: round(float(v), 4) for k, v in cumulative.items()}
    # Step 7: Charts
    print(f"[7/7] Generating charts...")
    charts = generate_charts(ChartInput(
        ticker=ticker,
        fund_name=metadata.name,
        monthly_prices=monthly_prices_for_chart,
        factor_loadings=regression.factor_loadings,
        factor_tstats=regression.factor_tstats,
        rolling_windows=[w.model_dump() for w in drift.rolling_windows],
        drift_events=[e.model_dump() for e in drift.drift_events]
    ))
    if charts.error:
        print(f"  Warning: {charts.error}")
    report["charts"] = {
        "nav_chart_json": charts.nav_chart_json,
        "loadings_chart_json": charts.loadings_chart_json,
        "rolling_chart_json": charts.rolling_chart_json,
    }
    print(f"  Charts generated successfully")

    # Step 8: Claude narrative
    print(f"[8/8] Generating narrative...")
    narrative = _generate_narrative(report)
    report["narrative"] = narrative
    print(f"  Narrative length: {len(narrative)} chars")

    print(f"\nAnalysis complete for {ticker}")
    return report

def _generate_narrative(report: dict) -> str:
    """
    Sends the quantitative results to Claude Sonnet for plain-English interpretation.
    Returns the narrative as a string.
    """
    # Build a clean summary for Claude - exclude chart JSONs (too large)
    payload = {
        "ticker": report["ticker"],
        "metadata": report["metadata"],
        "regression": report["regression"],
        "drift_summary": {
            "num_windows": report["drift"]["num_windows"],
            "num_drift_events": len(report["drift"]["drift_events"]),
            # Send only the top 10 most significant drift events by z-score
            "top_drift_events": sorted(
                report["drift"]["drift_events"],
                key=lambda x: abs(x["z_score"]),
                reverse=True
            )[:10],
        },
        "holdings": {
            "fund_name": report["holdings"]["fund_name"],
            "period_ending": report["holdings"]["period_ending"],
            "total_holdings": report["holdings"]["total_holdings"],
            "top10_concentration": report["holdings"]["top10_concentration"],
            "top_holdings": report["holdings"]["top_holdings"][:10] if report["holdings"]["top_holdings"] else [],
        } if report["holdings"] else None,
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Write the fund analysis narrative for the following data:\n\n{json.dumps(payload, indent=2)}"
            }
        ]
    )

    return response.content[0].text


if __name__ == "__main__":
    # Test with ARKK - we know its story
    report = run_agent("ARKK")

    print("\n" + "="*60)
    print("NARRATIVE OUTPUT")
    print("="*60)
    print(report["narrative"])

    if report["error"]:
        print(f"\nERROR: {report['error']}")



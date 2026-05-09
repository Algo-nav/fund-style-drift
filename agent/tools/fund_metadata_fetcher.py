# agent/tools/fund_metadata_fetcher.py

import requests
import os
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# Hardcoded metadata for the 34-fund universe.
# AUM figures are approximate as of early 2026. Expense ratios are exact.
FUND_UNIVERSE = {
    # ETFs
    "SPY":  {"name": "SPDR S&P 500 ETF Trust",             "category": "Large Blend",        "aum_usd": 550_000_000_000, "expense_ratio": 0.0009, "inception_date": "1993-01-22", "exchange": "NYSE"},
    "VOO":  {"name": "Vanguard S&P 500 ETF",               "category": "Large Blend",        "aum_usd": 480_000_000_000, "expense_ratio": 0.0003, "inception_date": "2010-09-07", "exchange": "NYSE"},
    "QQQ":  {"name": "Invesco QQQ Trust",                  "category": "Large Growth",       "aum_usd": 290_000_000_000, "expense_ratio": 0.0020, "inception_date": "1999-03-10", "exchange": "NASDAQ"},
    "IWM":  {"name": "iShares Russell 2000 ETF",           "category": "Small Blend",        "aum_usd": 72_000_000_000,  "expense_ratio": 0.0019, "inception_date": "2000-05-22", "exchange": "NYSE"},
    "SPYG": {"name": "SPDR S&P 500 Growth ETF",            "category": "Large Growth",       "aum_usd": 28_000_000_000,  "expense_ratio": 0.0004, "inception_date": "2000-09-25", "exchange": "NYSE"},
    "SPYV": {"name": "SPDR S&P 500 Value ETF",             "category": "Large Value",        "aum_usd": 23_000_000_000,  "expense_ratio": 0.0004, "inception_date": "2000-09-25", "exchange": "NYSE"},
    "VTV":  {"name": "Vanguard Value ETF",                 "category": "Large Value",        "aum_usd": 120_000_000_000, "expense_ratio": 0.0004, "inception_date": "2004-01-26", "exchange": "NYSE"},
    "VUG":  {"name": "Vanguard Growth ETF",                "category": "Large Growth",       "aum_usd": 140_000_000_000, "expense_ratio": 0.0004, "inception_date": "2004-01-26", "exchange": "NYSE"},
    "MTUM": {"name": "iShares MSCI USA Momentum ETF",      "category": "Large Growth",       "aum_usd": 14_000_000_000,  "expense_ratio": 0.0015, "inception_date": "2013-04-16", "exchange": "NASDAQ"},
    "QUAL": {"name": "iShares MSCI USA Quality ETF",       "category": "Large Blend",        "aum_usd": 42_000_000_000,  "expense_ratio": 0.0015, "inception_date": "2013-07-16", "exchange": "NASDAQ"},
    "USMV": {"name": "iShares MSCI USA Min Vol ETF",       "category": "Large Blend",        "aum_usd": 26_000_000_000,  "expense_ratio": 0.0015, "inception_date": "2011-10-18", "exchange": "NYSE"},
    "SPLV": {"name": "Invesco S&P 500 Low Volatility ETF", "category": "Large Blend",        "aum_usd": 8_000_000_000,   "expense_ratio": 0.0025, "inception_date": "2011-05-05", "exchange": "NYSE"},
    "VYM":  {"name": "Vanguard High Dividend Yield ETF",   "category": "Large Value",        "aum_usd": 60_000_000_000,  "expense_ratio": 0.0006, "inception_date": "2006-11-10", "exchange": "NYSE"},
    "DGRO": {"name": "iShares Core Dividend Growth ETF",   "category": "Large Blend",        "aum_usd": 28_000_000_000,  "expense_ratio": 0.0008, "inception_date": "2014-06-10", "exchange": "NYSE"},
    "ARKK": {"name": "ARK Innovation ETF",                 "category": "Mid Growth",         "aum_usd": 7_000_000_000,   "expense_ratio": 0.0075, "inception_date": "2014-10-31", "exchange": "NYSE"},
    "ARKG": {"name": "ARK Genomic Revolution ETF",         "category": "Health",             "aum_usd": 2_000_000_000,   "expense_ratio": 0.0075, "inception_date": "2014-10-31", "exchange": "NYSE"},
    "XLK":  {"name": "Technology Select Sector SPDR",      "category": "Technology",         "aum_usd": 75_000_000_000,  "expense_ratio": 0.0009, "inception_date": "1998-12-16", "exchange": "NYSE"},
    "XLF":  {"name": "Financial Select Sector SPDR",       "category": "Financials",         "aum_usd": 45_000_000_000,  "expense_ratio": 0.0009, "inception_date": "1998-12-16", "exchange": "NYSE"},
    "XLE":  {"name": "Energy Select Sector SPDR",          "category": "Energy",             "aum_usd": 38_000_000_000,  "expense_ratio": 0.0009, "inception_date": "1998-12-16", "exchange": "NYSE"},
    "XLV":  {"name": "Health Care Select Sector SPDR",     "category": "Healthcare",         "aum_usd": 40_000_000_000,  "expense_ratio": 0.0009, "inception_date": "1998-12-16", "exchange": "NYSE"},
    # Mutual funds
    "VFINX": {"name": "Vanguard 500 Index Fund",           "category": "Large Blend",        "aum_usd": 430_000_000_000, "expense_ratio": 0.0014, "inception_date": "1976-08-31", "exchange": "MUTF"},
    "VWUSX": {"name": "Vanguard US Growth Fund",           "category": "Large Growth",       "aum_usd": 12_000_000_000,  "expense_ratio": 0.0038, "inception_date": "1959-01-06", "exchange": "MUTF"},
    "FCNTX": {"name": "Fidelity Contrafund",               "category": "Large Growth",       "aum_usd": 120_000_000_000, "expense_ratio": 0.0039, "inception_date": "1967-05-17", "exchange": "MUTF"},
    "FXAIX": {"name": "Fidelity 500 Index Fund",           "category": "Large Blend",        "aum_usd": 550_000_000_000, "expense_ratio": 0.0002, "inception_date": "1988-02-17", "exchange": "MUTF"},
    "AGTHX": {"name": "American Funds Growth Fund",        "category": "Large Growth",       "aum_usd": 230_000_000_000, "expense_ratio": 0.0064, "inception_date": "1973-12-01", "exchange": "MUTF"},
    "AIVSX": {"name": "American Funds Investment Co",      "category": "Large Blend",        "aum_usd": 150_000_000_000, "expense_ratio": 0.0057, "inception_date": "1934-01-01", "exchange": "MUTF"},
    "PRGFX": {"name": "T. Rowe Price Growth Stock Fund",   "category": "Large Growth",       "aum_usd": 55_000_000_000,  "expense_ratio": 0.0064, "inception_date": "1950-04-11", "exchange": "MUTF"},
    "PRFDX": {"name": "T. Rowe Price Dividend Growth",     "category": "Large Blend",        "aum_usd": 18_000_000_000,  "expense_ratio": 0.0062, "inception_date": "1992-12-30", "exchange": "MUTF"},
    "JAVLX": {"name": "Janus Henderson Forty Fund",        "category": "Large Growth",       "aum_usd": 8_000_000_000,   "expense_ratio": 0.0064, "inception_date": "1997-05-01", "exchange": "MUTF"},
    "MFEKX": {"name": "MFS Massachusetts Investors Trust", "category": "Large Blend",        "aum_usd": 6_000_000_000,   "expense_ratio": 0.0071, "inception_date": "1924-03-21", "exchange": "MUTF"},
    "LMOPX": {"name": "Legg Mason Opportunity Trust",      "category": "Mid Blend",          "aum_usd": 2_000_000_000,   "expense_ratio": 0.0108, "inception_date": "1933-01-01", "exchange": "MUTF"},
    "CGMFX": {"name": "CGM Focus Fund",                    "category": "Large Blend",        "aum_usd": 1_000_000_000,   "expense_ratio": 0.0091, "inception_date": "1997-09-02", "exchange": "MUTF"},
    "SEQUX": {"name": "Sequoia Fund",                      "category": "Large Blend",        "aum_usd": 3_000_000_000,   "expense_ratio": 0.0110, "inception_date": "1970-07-15", "exchange": "MUTF"},
    "DODGX": {"name": "Dodge & Cox Stock Fund",            "category": "Large Value",        "aum_usd": 90_000_000_000,  "expense_ratio": 0.0052, "inception_date": "1965-01-04", "exchange": "MUTF"},
}


class FundMetadataInput(BaseModel):
    ticker: str


class FundMetadataOutput(BaseModel):
    ticker: str
    name: str
    category: Optional[str] = None
    aum_usd: Optional[float] = None
    expense_ratio: Optional[float] = None
    inception_date: Optional[str] = None
    exchange: Optional[str] = None
    in_universe: bool = False    # True if ticker is in the hardcoded universe
    source: str
    error: Optional[str] = None


def get_fund_metadata(inp: FundMetadataInput) -> FundMetadataOutput:
    ticker = inp.ticker.upper().strip()

    # Primary: hardcoded universe
    if ticker in FUND_UNIVERSE:
        d = FUND_UNIVERSE[ticker]
        return FundMetadataOutput(
            ticker=ticker,
            name=d["name"],
            category=d["category"],
            aum_usd=d["aum_usd"],
            expense_ratio=d["expense_ratio"],
            inception_date=d["inception_date"],
            exchange=d["exchange"],
            in_universe=True,
            source="Fund universe lookup table (static, as of early 2026)",
            error=None
        )

    # Fallback: FMP profile endpoint for unknown tickers
    try:
        url = f"{FMP_BASE}/profile/{ticker}?apikey={FMP_API_KEY}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list) and len(data) > 0:
            d = data[0]
            return FundMetadataOutput(
                ticker=ticker,
                name=d.get("companyName") or ticker,
                category=d.get("industry") or d.get("sector"),
                aum_usd=None,
                expense_ratio=None,
                inception_date=d.get("ipoDate"),
                exchange=d.get("exchangeShortName"),
                in_universe=False,
                source="Financial Modeling Prep profile endpoint",
                error=None
            )
    except Exception as e:
        pass

    # Last resort: return ticker with nulls
    return FundMetadataOutput(
        ticker=ticker,
        name=ticker,
        in_universe=False,
        source="Unknown",
        error=f"No metadata found for {ticker}"
    )


if __name__ == "__main__":
    # Test universe fund, and an unknown ticker
    for ticker in ["QQQ", "ARKK", "VFINX", "DODGX", "MSFT"]:
        result = get_fund_metadata(FundMetadataInput(ticker=ticker))
        print(f"\n{result.ticker} (in_universe={result.in_universe})")
        print(f"  Name: {result.name}")
        print(f"  Category: {result.category}")
        print(f"  AUM: ${result.aum_usd:,.0f}" if result.aum_usd else "  AUM: N/A")
        print(f"  Expense ratio: {result.expense_ratio}" if result.expense_ratio else "  Expense ratio: N/A")
        print(f"  Inception: {result.inception_date}")
        print(f"  Error: {result.error}")
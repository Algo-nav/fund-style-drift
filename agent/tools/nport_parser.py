# agent/tools/nport_parser.py

import requests
import xml.etree.ElementTree as ET
import pandas as pd
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# EDGAR requires a user-agent header
HEADERS = {"User-Agent": "Navneet Danturi navneet@example.com"}

# N-PORT XML namespaces
NS = {
    "nport": "http://www.sec.gov/edgar/nport",
    "com":   "http://www.sec.gov/edgar/common"
}


class Holding(BaseModel):
    name: str
    ticker: Optional[str] = None
    pct_weight: float    # percentage of fund NAV (as reported, e.g. 5.23 means 5.23%)
    value_usd: float


class NportInput(BaseModel):
    ticker: str          # fund ticker e.g. "VFINX"
    max_holdings: int = 20   # how many top holdings to return


class NportOutput(BaseModel):
    ticker: str
    fund_name: str
    period_ending: str       # "YYYY-MM-DD"
    filed_date: str          # "YYYY-MM-DD"
    total_holdings: int      # total number of securities in the filing
    top_holdings: list[Holding]
    top10_concentration: float   # sum of top 10 weights as a percentage
    source: str
    error: Optional[str] = None


def _get_cik(ticker: str) -> Optional[str]:
    """Look up EDGAR CIK for a given ticker using the company search API."""
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=NPORT-P&dateb=&owner=include&count=5&search_text=&action=getcompany&output=atom"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.content)
    ns_atom = {"atom": "http://www.w3.org/2005/Atom"}
    cik_el = root.find(".//atom:cik", ns_atom)
    if cik_el is not None and cik_el.text:
        return cik_el.text.strip()

    return None


def _get_latest_filing(cik: str) -> Optional[dict]:
    """
    Get the most recent NPORT-P filing accession number and metadata
    for a given CIK using the EDGAR submissions API.
    """
    cik_padded = cik.lstrip("0").zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    filing_dates = filings.get("filingDate", [])
    report_dates = filings.get("reportDate", [])

    # Find the most recent NPORT-P filing
    for i, form in enumerate(forms):
        if form == "NPORT-P":
            return {
                "accession": accessions[i],
                "filed_date": filing_dates[i],
                "period_ending": report_dates[i]
            }
    return None


def _fetch_holdings(cik: str, accession: str) -> tuple[list[dict], str]:
    """
    Fetch and parse holdings from the primary_doc.xml of an N-PORT filing.
    Returns (holdings_list, fund_name).
    """
    cik_short = cik.lstrip("0")
    accession_clean = accession.replace("-", "")

    url = f"https://www.sec.gov/Archives/edgar/data/{cik_short}/{accession_clean}/primary_doc.xml"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    # Fund name from genInfo
    fund_name = root.findtext(".//nport:regName", default="Unknown", namespaces=NS)

    # Parse holdings
    investments = root.findall(".//nport:invstOrSec", NS)
    holdings = []
    for inv in investments:
        name = inv.findtext("nport:name", default="N/A", namespaces=NS)
        ticker = inv.findtext("nport:ticker", default=None, namespaces=NS)
        pct_raw = inv.findtext("nport:pctVal", default="0", namespaces=NS)
        val_raw = inv.findtext("nport:valUSD", default="0", namespaces=NS)

        try:
            pct = float(pct_raw.strip().replace("%", ""))
            val = float(val_raw.strip())
        except (ValueError, AttributeError):
            pct = 0.0
            val = 0.0

        holdings.append({
            "name": name,
            "ticker": ticker if ticker and ticker.strip() else None,
            "pct_weight": round(pct, 6),
            "value_usd": round(val, 2)
        })

    return holdings, fund_name


def parse_nport(inp: NportInput) -> NportOutput:
    try:
        # Step 1: CIK lookup
        cik = _get_cik(inp.ticker)
        if not cik:
            raise ValueError(f"Could not find CIK for ticker {inp.ticker}")

        # Step 2: Find latest filing
        filing = _get_latest_filing(cik)
        if not filing:
            raise ValueError(f"No NPORT-P filing found for CIK {cik}")

        # Step 3: Fetch and parse holdings
        holdings_raw, fund_name = _fetch_holdings(cik, filing["accession"])

        if not holdings_raw:
            raise ValueError("No holdings found in filing")

        # Sort by weight descending
        holdings_raw.sort(key=lambda x: x["pct_weight"], reverse=True)

        total_holdings = len(holdings_raw)

        # Top 10 concentration
        top10_weights = [h["pct_weight"] for h in holdings_raw[:10]]
        top10_concentration = round(sum(top10_weights), 4)

        # Top N holdings as Holding objects
        top_holdings = [
            Holding(**h) for h in holdings_raw[:inp.max_holdings]
        ]

        return NportOutput(
            ticker=inp.ticker,
            fund_name=fund_name,
            period_ending=filing["period_ending"],
            filed_date=filing["filed_date"],
            total_holdings=total_holdings,
            top_holdings=top_holdings,
            top10_concentration=top10_concentration,
            source=f"SEC EDGAR N-PORT filing. Accession: {filing['accession']}",
            error=None
        )

    except Exception as e:
        return NportOutput(
            ticker=inp.ticker,
            fund_name="Unknown",
            period_ending="N/A",
            filed_date="N/A",
            total_holdings=0,
            top_holdings=[],
            top10_concentration=0.0,
            source="SEC EDGAR N-PORT",
            error=str(e)
        )


if __name__ == "__main__":
    result = parse_nport(NportInput(ticker="VFINX", max_holdings=10))
    print(f"Ticker: {result.ticker}")
    print(f"Fund: {result.fund_name}")
    print(f"Period ending: {result.period_ending}")
    print(f"Filed: {result.filed_date}")
    print(f"Error: {result.error}")
    print(f"Total holdings: {result.total_holdings}")
    print(f"Top 10 concentration: {result.top10_concentration}%")
    print(f"\nTop 10 holdings:")
    for i, h in enumerate(result.top_holdings, 1):
        ticker_str = f"({h.ticker})" if h.ticker else ""
        print(f"  {i}. {h.name} {ticker_str} - {h.pct_weight:.4f}%")
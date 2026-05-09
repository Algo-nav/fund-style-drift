# scripts/pregenerate.py
#
# Pre-generates fund style drift reports for all 33 funds in the universe.
# Outputs one JSON file per fund to outputs/reports/.
# Run this script to refresh the gallery before deploying to HF Spaces.
#
# Usage:
#   python -m scripts.pregenerate
#   python -m scripts.pregenerate --tickers QQQ ARKK VFINX  (subset)
#   python -m scripts.pregenerate --refresh  (re-run all, overwrite existing)

import os
import json
import argparse
import time
from pathlib import Path
from agent.agent import run_agent

OUTPUT_DIR = Path("outputs/reports")

FUND_UNIVERSE = [
    # ETFs
    "SPY", "VOO", "QQQ", "IWM", "SPYG", "SPYV", "VTV", "VUG",
    "MTUM", "QUAL", "USMV", "SPLV", "VYM", "DGRO", "ARKK", "ARKG",
    "XLK", "XLF", "XLE", "XLV",
    # Mutual funds
    "VFINX", "VWUSX", "FCNTX", "FXAIX", "AGTHX", "AIVSX",
    "PRGFX", "PRFDX", "MFEKX", "LMOPX", "CGMFX", "SEQUX", "DODGX"
]


def save_report(ticker: str, report: dict) -> Path:
    """Save a report dict to outputs/reports/{ticker}.json"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{ticker}.json"

    # Charts are large JSON strings - keep them in the output
    # but strip rolling_windows from the drift section to reduce file size.
    # Rolling windows are only needed for chart rendering, which is done at generation time.
    report_to_save = report.copy()
    if report_to_save.get("drift"):
        report_to_save["drift"] = {
            "num_windows": report_to_save["drift"]["num_windows"],
            "drift_events": report_to_save["drift"]["drift_events"],
            # rolling_windows excluded - already baked into chart JSON
        }

    with open(path, "w") as f:
        json.dump(report_to_save, f, indent=2)

    return path


def run_pregeneration(tickers: list, refresh: bool = False) -> None:
    results = []
    total = len(tickers)

    print(f"\nPre-generating {total} fund reports...")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    print(f"Refresh mode: {refresh}")
    print("="*60)

    for i, ticker in enumerate(tickers, 1):
        output_path = OUTPUT_DIR / f"{ticker}.json"

        # Skip if already exists and not refreshing
        if output_path.exists() and not refresh:
            print(f"[{i}/{total}] {ticker}: skipping (already exists)")
            results.append((ticker, "skipped", None))
            continue

        print(f"[{i}/{total}] {ticker}: running...")

        try:
            report = run_agent(ticker)
            pipeline_error = report.get("error")

            if pipeline_error:
                print(f"  ERROR: {pipeline_error}")
                results.append((ticker, "failed", pipeline_error))
                continue

            path = save_report(ticker, report)
            size_kb = path.stat().st_size / 1024
            narrative_len = len(report.get("narrative", "") or "")
            holdings_error = report.get("holdings", {}).get("error")

            status = "ok" if not holdings_error else "ok (no holdings)"
            print(f"  Done: {size_kb:.0f}KB, narrative={narrative_len} chars, status={status}")
            results.append((ticker, status, None))

        except Exception as e:
            print(f"  EXCEPTION: {e}")
            results.append((ticker, "exception", str(e)))

        # Small delay between funds to avoid rate limiting
        if i < total:
            time.sleep(2)

    # Final summary
    print("\n" + "="*60)
    print("PRE-GENERATION SUMMARY")
    print("="*60)
    ok = [r for r in results if r[1] in ("ok", "ok (no holdings)")]
    skipped = [r for r in results if r[1] == "skipped"]
    failed = [r for r in results if r[1] in ("failed", "exception")]

    print(f"Success:  {len(ok)}/{total}")
    print(f"Skipped:  {len(skipped)}/{total}")
    print(f"Failed:   {len(failed)}/{total}")

    if failed:
        print("\nFailures:")
        for ticker, status, error in failed:
            print(f"  {ticker}: {error}")

    print(f"\nReports saved to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-generate fund style drift reports")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Specific tickers to generate (default: all 33)"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-run and overwrite existing reports"
    )
    args = parser.parse_args()

    tickers = args.tickers if args.tickers else FUND_UNIVERSE
    tickers = [t.upper() for t in tickers]

    run_pregeneration(tickers, refresh=args.refresh)
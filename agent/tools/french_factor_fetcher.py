from pydantic import BaseModel
from typing import Optional
import pandas as pd


class FrenchFactorInput(BaseModel):
    start_date: str  # format: "YYYY-MM"
    end_date: str    # format: "YYYY-MM"
    refresh: bool = False  # if True, re-download even if cache exists


class FrenchFactorOutput(BaseModel):
    factors: dict        # {date_str: {factor_name: value}} - explained below
    start_date: str
    end_date: str
    num_observations: int
    factors_available: list[str]
    source: str
    cache_used: bool
    error: Optional[str] = None


# agent/tools/french_factor_fetcher.py

import os
import io
import zipfile
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional

load_dotenv()

# Cache directory - matches folder structure above
CACHE_DIR = Path("data/french_factors")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FF5_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
MOM_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"

FF5_CACHE = CACHE_DIR / "ff5_monthly.csv"
MOM_CACHE = CACHE_DIR / "mom_monthly.csv"


class FrenchFactorInput(BaseModel):
    start_date: str   # "YYYY-MM"
    end_date: str     # "YYYY-MM"
    refresh: bool = False


class FrenchFactorOutput(BaseModel):
    factors: dict
    start_date: str
    end_date: str
    num_observations: int
    factors_available: list[str]
    source: str
    cache_used: bool
    error: Optional[str] = None


def _download_and_parse(url: str, cache_path: Path) -> pd.DataFrame:
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            raw = f.read().decode("utf-8", errors="replace")

    lines = raw.splitlines()

    # Find the first data row (6-digit YYYYMM after splitting by comma)
    # The line immediately before it is the header
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        first_token = stripped.split(",")[0].strip()
        if len(first_token) == 6 and first_token.isdigit():
            header_idx = i - 1
            break

    if header_idx is None:
        raise ValueError("Could not find data rows in French factor file")

    # Keep header + only rows where first token is 6-digit YYYYMM
    kept = [lines[header_idx]]
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        first_token = stripped.split(",")[0].strip()
        if len(first_token) == 6 and first_token.isdigit():
            kept.append(stripped)

    from io import StringIO
    df = pd.read_csv(
        StringIO("\n".join(kept)),
        sep=",",
        index_col=0
    )

    df.columns = df.columns.str.strip()
    df.index = pd.to_datetime(df.index.astype(str).str.strip(), format="%Y%m")
    df.index.name = "date"
    df = df.astype(float) / 100.0

    df.to_csv(cache_path)
    return df

def _load_or_download(url: str, cache_path: Path, refresh: bool) -> pd.DataFrame:
    if cache_path.exists() and not refresh:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df
    return _download_and_parse(url, cache_path)


def get_french_factors(inp: FrenchFactorInput) -> FrenchFactorOutput:
    try:
        ff5 = _load_or_download(FF5_URL, FF5_CACHE, inp.refresh)
        mom = _load_or_download(MOM_URL, MOM_CACHE, inp.refresh)

        # FF5 columns: Mkt-RF, SMB, HML, RMW, CMA, RF
        # Mom column: Mom
        # Rename Mom column defensively (sometimes named "Mom" or "WML")
        mom.columns = ["Mom"]

        # Merge on date index - inner join keeps only months both files have
        combined = ff5.join(mom, how="inner")

        # Filter to requested date range
        start = pd.to_datetime(inp.start_date, format="%Y-%m")
        end = pd.to_datetime(inp.end_date, format="%Y-%m")
        combined = combined.loc[start:end]

        if combined.empty:
            return FrenchFactorOutput(
                factors={},
                start_date=inp.start_date,
                end_date=inp.end_date,
                num_observations=0,
                factors_available=[],
                source="Ken French Data Library",
                cache_used=not inp.refresh,
                error="No data in requested date range"
            )

        # Convert to JSON-serializable dict
        # Key: "YYYY-MM", value: dict of factor_name -> float
        factors_dict = {}
        for date, row in combined.iterrows():
            key = date.strftime("%Y-%m")
            factors_dict[key] = {col: round(float(row[col]), 6) for col in combined.columns}

        return FrenchFactorOutput(
            factors=factors_dict,
            start_date=combined.index[0].strftime("%Y-%m"),
            end_date=combined.index[-1].strftime("%Y-%m"),
            num_observations=len(combined),
            factors_available=list(combined.columns),
            source="Ken French Data Library (https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)",
            cache_used=not inp.refresh,
            error=None
        )

    except Exception as e:
        return FrenchFactorOutput(
            factors={},
            start_date=inp.start_date,
            end_date=inp.end_date,
            num_observations=0,
            factors_available=[],
            source="Ken French Data Library",
            cache_used=False,
            error=str(e)
        )


if __name__ == "__main__":
    result = get_french_factors(FrenchFactorInput(
        start_date="2019-01",
        end_date="2024-12"
    ))
    print(f"Error: {result.error}")
    print(f"Observations: {result.num_observations}")
    print(f"Factors: {result.factors_available}")
    print(f"Cache used: {result.cache_used}")
    if result.factors:
        # Print first 3 months as a sanity check
        for i, (date, vals) in enumerate(result.factors.items()):
            print(f"{date}: {vals}")
            if i >= 2:
                break
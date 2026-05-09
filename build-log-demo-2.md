# Fund Style Drift Detector — Build Log

**Project:** Demo #2 — Fund Style Drift Detector (v1)
**Hugging Face:** huggingface.co/spaces/Nav772/fund-style-drift (stub, not yet deployed)
**GitHub:** github.com/Algo-nav/fund-style-drift (stub, not yet deployed)
**Working mode:** Heavy teaching (14-16 week target)

---

## Week 1 — Environment Setup and Track 1 (Ken French Data)

**Goal:** Local environment configured, Ken French FF6 factor data pipeline built, validated, and committed.

### Environment

- Project folder: `~/Desktop/Projects-2.0/fund-style-drift`
- Python 3.12, virtual environment via `venv`
- VS Code with interpreter pointed at project venv
- `.env` file for secrets (gitignored), `requirements.txt` committed
- Git initialized, first commit at clean foundation

### Packages Installed (Week 1)

- `pandas` - data spine for all time-series work
- `numpy` - numerical operations
- `statsmodels` - OLS regression (installed early for Track 2 preview)
- `requests` - HTTP for Ken French CSV downloads
- `python-dotenv` - environment variable loading
- `pydantic` - input/output validation on every tool

### Folder Structure

```
fund-style-drift/
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   └── tools/
│       ├── __init__.py
│       ├── french_factor_fetcher.py   # Track 1 - complete
│       ├── fund_price_fetcher.py      # Track 2 - pending
│       ├── nport_parser.py            # Track 3 - pending
│       ├── fund_metadata_fetcher.py   # week 2+
│       ├── factor_regression_engine.py
│       ├── drift_detection_engine.py
│       └── chart_generator.py
├── prompts/
│   └── style_drift.py
├── data/
│   └── french_factors/               # cached FF5 and Mom CSVs
├── outputs/                          # pre-generated reports land here
├── notebooks/                        # week 1 validation notebooks (temp)
├── scripts/
│   ├── verify_keys.py
│   └── pregenerate.py
├── .env
├── .gitignore
├── app.py
├── requirements.txt
├── README.md
└── v2-ideas.md
```

### Track 1: Ken French FF6 Factor Fetcher

**File:** `agent/tools/french_factor_fetcher.py`

**What it does:**
- Downloads FF5 monthly factors (Mkt-RF, SMB, HML, RMW, CMA, RF) from the Ken French data library at Dartmouth.
- Downloads Momentum factor (Mom) from a separate French library file.
- Parses both files, merges on date index (inner join), converts from percent to decimal, and caches to `data/french_factors/` as CSV.
- Filters to a requested date range and returns a JSON-serializable dict keyed by `YYYY-MM`.
- Returns partial results with an error field on failure rather than crashing.

**Pydantic schemas:**
- `FrenchFactorInput`: `start_date` (YYYY-MM), `end_date` (YYYY-MM), `refresh` (bool, default False).
- `FrenchFactorOutput`: `factors` dict, `start_date`, `end_date`, `num_observations`, `factors_available`, `source`, `cache_used`, `error`.

**Patterns established (carry forward to all tools):**
- Pydantic `BaseModel` for every input and output.
- `source` field on every output schema for citation grounding.
- `Optional[error]` field for graceful failure reporting.
- `try/except` at the top level, return partial results not crashes.
- `if __name__ == "__main__"` test block in every tool file.
- Cache-first: read from disk if cache exists, download only if missing or `refresh=True`.

**Parsing issues resolved:**

| Issue | Resolution |
|---|---|
| `pd.read_csv` failing with "Expected 7 fields, saw 9" | Annual summary rows at bottom of file have extra columns. Fixed by filtering to only rows where first comma-delimited token is a 6-digit YYYYMM date. |
| "Could not find header row" on Mom file | Original fix searched for "Mkt-RF" string which doesn't exist in the Mom file. Fixed by finding the header as the line immediately before the first data row, making the parser generic across both files. |
| `ModuleNotFoundError: No module named 'pydantic'` | Pydantic omitted from week 1 install command. Added and requirements.txt updated. |

**Validation results (2019-01 to 2024-12):**
- Observations: 72 (correct: 6 years x 12 months)
- Factors: `['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF', 'Mom']` (all 7 confirmed)
- Cache: writes on first run, reads on subsequent runs (confirmed)
- Sample values (2019-01): Mkt-RF 0.0836, Mom -0.0862 (January 2019 was a strong recovery month after December 2018 selloff - values are correct)

### Commits

| Hash | Message |
|---|---|
| (initial) | Initial project setup: structure, dependencies |
| (track 1) | Week 1 Track 1: Ken French FF6 factor fetcher with caching |
| (track 2) | Week 1 Track 2: ETF price fetcher with monthly returns and data quality check |
| (date range) | Extend date range to 2025-12 across all tools |

---

## Week 1 — Complete

| Track | Goal | Status |
|---|---|---|
| Track 1 | Ken French FF6 data pipeline | Complete |
| Track 2 | ETF price data via yfinance, monthly returns, single OLS regression in notebook | Complete |
| Track 3 | Mutual fund NAV validation (yfinance/FMP), N-PORT XML parsing on 1 fund | Complete |

### Track 2: ETF Price Fetcher

**File:** `agent/tools/fund_price_fetcher.py`

**What it does:**
- Pulls monthly adjusted close prices via yfinance for any ticker.
- Computes monthly returns via `pct_change()`.
- Normalizes timestamps to month-end to align with French factor dates.
- Checks for missing months in the requested date range and reports them in a `missing_months` field.
- Returns raw returns only. RF subtraction (excess returns) happens in the regression engine, not here.

**Pydantic schemas:**
- `FundPriceInput`: `ticker`, `start_date` (YYYY-MM), `end_date` (YYYY-MM).
- `FundPriceOutput`: `ticker`, `returns` dict, `start_date`, `end_date`, `num_observations`, `missing_months`, `source`, `error`.

**Date range decision:** Extended from `2024-12` to `2025-12` across all tools. Gives 84 observations (7 years) instead of 72. 2026 excluded because only 3 months of data exist, creating a partial-year edge case.

**Validation results (QQQ, 2019-01 to 2025-12):**
- Observations: 84, missing months: 0
- January 2019 return: 0.0932 (strong recovery month, correct)

### Track 3: Mutual Fund NAV and N-PORT Validation

**Question 1 - yfinance mutual fund NAV:** Confirmed clean. VFINX, FCNTX, AGTHX all returned 84 rows with no gaps. No FMP fallback needed for NAV data.

**Question 2 - N-PORT XML parsing:** Confirmed feasible. 515 holdings parsed from VFINX September 2024 filing using the standard library (`xml.etree.ElementTree`). No paid parsing tools needed.

**Scope impact:** No changes. Mutual funds stay in v1. ETF-only fallback not needed.

---

## Week 2 — Factor Regression Engine and N-PORT Parser

**Goal:** Wrap the notebook regression into a production tool. Build the N-PORT parser as a proper Pydantic tool.

### Packages Added (Week 2)

- `scipy` - Jarque-Bera normality test for residual diagnostics
- `yfinance` - ETF and mutual fund price data
- `jupyter` - validation notebooks (temp, not shipped)

### Tool: Factor Regression Engine

**File:** `agent/tools/factor_regression_engine.py`

**What it does:**
- Takes fund returns (from `fund_price_fetcher`) and factor data (from `french_factor_fetcher`) as inputs.
- Aligns both series on month-end date index.
- Computes excess returns (fund return minus RF).
- Runs OLS regression via statsmodels.
- Returns factor loadings, t-stats, p-values, r-squared, alpha, and four confidence dimensions.

**Confidence dimensions (never collapsed into a single score):**

| Dimension | Metric | Thresholds |
|---|---|---|
| Fit | Adj. R-squared | high (>=0.70), moderate (0.40-0.70), low (<0.40) |
| Significance | Count of factors with abs(t-stat) >= 2.0 | high (4+), moderate (2-3), low (0-1) |
| Sample | Number of observations | adequate (36+), marginal (24-35), insufficient (<24) |
| Normality | Jarque-Bera p-value on residuals | pass (>=0.05), flag (<0.05) |

**Pydantic schemas:**
- `ConfidenceDimension`: `label`, `metric`, `metric_name`.
- `FactorRegressionInput`: `ticker`, `returns` dict, `factors` dict, `start_date`, `end_date`.
- `FactorRegressionOutput`: full regression results + four `ConfidenceDimension` fields + `source` + `error`.

**Validation results (QQQ, 2019-01 to 2025-12):**
- Observations: 84
- Alpha: 0.003081 (t=2.01, p=0.048) - marginally significant
- R-squared: 0.9506, Adj R-squared: 0.9467
- Significant factors (4/6): Mkt-RF (t=31.9), SMB (t=-3.4), HML (t=-6.7), Mom (t=-2.8)
- Non-significant: RMW (t=-0.75), CMA (t=-0.10)
- Confidence: Fit=high, Significance=high, Sample=adequate, Normality=pass

### Tool: N-PORT Parser

**File:** `agent/tools/nport_parser.py`

**What it does:**
- Looks up EDGAR CIK from a ticker using the EDGAR company search atom feed.
- Finds the most recent NPORT-P filing accession number via the EDGAR submissions API.
- Fetches and parses `primary_doc.xml` from the filing.
- Returns top N holdings sorted by weight, total holdings count, and top 10 concentration.

**Parsing issues resolved:**

| Issue | Resolution |
|---|---|
| CIK lookup returning zero hits via full-text search | Switched to EDGAR company search atom feed (`browse-edgar?output=atom`). |
| Atom feed `<cik>` tag not found | Tag carries the Atom namespace (`http://www.w3.org/2005/Atom`). Fixed by using `atom:cik` in the namespace-aware find. |

**Validation results (VFINX, most recent filing):**
- Fund: VANGUARD INDEX FUNDS
- Period ending: 2025-12-31, filed: 2026-02-26
- Total holdings: 323
- Top 10 concentration: 20.60%
- Top holding: JPMorgan Chase (3.56%)

### Commits (Week 2)

| Hash | Message |
|---|---|
| e02a76d | Week 2: factor regression engine with 4 confidence dimensions |
| 85db4a2 | Week 2: N-PORT parser with CIK lookup and holdings extraction |

---

---

## Week 3 — Drift Detection Engine

**Goal:** Build the rolling window regression and drift flagging logic.

### Tool: Drift Detection Engine

**File:** `agent/tools/drift_detection_engine.py`

**What it does:**
- Aligns fund returns and factor data on a shared date index.
- Runs OLS regression on a sliding 24-month window, stepping forward 1 month at a time.
- Produces a time series of factor loadings (one set per window).
- Flags drift when any factor loading moves more than 1.5 standard deviations from its prior history.
- Requires a minimum of 12 prior windows before flagging drift (avoids false positives early in the series).
- Returns all rolling windows and all drift events as structured Pydantic objects.

**Key constants:**
- Window size: 24 months.
- Step size: 1 month.
- Drift threshold: 1.5 standard deviations.
- Minimum history before flagging: 12 windows.

**Pydantic schemas:**
- `DriftEvent`: `date`, `factor`, `loading`, `historical_mean`, `historical_std`, `z_score`, `direction`.
- `RollingWindow`: `date`, `factor_loadings`, `adj_r_squared`, `num_observations`.
- `DriftDetectionInput`: `ticker`, `returns`, `factors`, `start_date`, `end_date`, `window_size`, `drift_threshold`.
- `DriftDetectionOutput`: `rolling_windows`, `drift_events`, `num_windows`, `factors_analyzed`, `source`, `error`.

**Validation results (ARKK, 2019-01 to 2025-12):**
- Windows computed: 61 (84 months - 24 window + 1 = 61, correct)
- Drift events detected: 105
- Notable events: Mkt-RF loading jumped to 2.01 (z=7.15) in February 2022 - peak speculation period before crash. RMW loading hit -1.19 (z=-5.67) in January 2022 - heavy tilt toward unprofitable companies at peak ARK valuations. Both historically accurate.
- First window ends: 2020-12 (correct: 2019-01 + 24 months)
- Last window ends: 2025-12 (correct)
- Adj R-squared stable above 0.70 throughout (high confidence fit)

### Commits (Week 3)

| Hash | Message |
|---|---|
| 3b2cf87 | Week 3: drift detection engine with rolling OLS and drift flagging |

---

## Week 4 — Fund Metadata Fetcher and Chart Generator

**Goal:** Complete the tool surface. Metadata fetcher for fund snapshot. Chart generator for all three Plotly charts.

### Packages Added (Week 4)

- `plotly` 6.7.0 - chart generation

### Tool: Fund Metadata Fetcher

**File:** `agent/tools/fund_metadata_fetcher.py`

**What it does:**
- Primary: returns metadata from a hardcoded lookup table for the 34-fund universe. Always clean, no API dependency.
- Fallback: if ticker not in universe, tries FMP profile endpoint for name, exchange, inception date.
- Last resort: returns ticker as name with nulls. Report still generates.

**Fund universe: 34 funds (20 ETFs, 14 mutual funds)**

ETFs: SPY, VOO, QQQ, IWM, SPYG, SPYV, VTV, VUG, MTUM, QUAL, USMV, SPLV, VYM, DGRO, ARKK, ARKG, XLK, XLF, XLE, XLV.

Mutual funds: VFINX, VWUSX, FCNTX, FXAIX, AGTHX, AIVSX, PRGFX, PRFDX, JAVLX, MFEKX, LMOPX, CGMFX, SEQUX, DODGX.

**Decision logged:** FMP ETF info endpoint returns 403 on Starter tier. Hardcoded lookup table chosen for v1. FMP profile endpoint retained as fallback for unknown tickers. VEIEX (emerging markets) excluded - not US equity.

**Validation results:**
- QQQ, ARKK, VFINX, DODGX: full metadata from lookup table, `in_universe=True`.
- MSFT: falls through to last resort gracefully, no crash, `in_universe=False`.

### Tool: Chart Generator

**File:** `agent/tools/chart_generator.py`

**What it does:**
- Builds three Plotly charts per fund report, all in dark theme matching HF Spaces dark mode.
- Returns each chart as a JSON string for embedding in Gradio UI.

**Charts:**

| Chart | Type | What it shows |
|---|---|---|
| NAV chart | Line with fill | Monthly price history over full period |
| Factor loadings | Horizontal bar | Current factor loadings, significant bars fully opaque, non-significant dimmed to 35% |
| Rolling exposures | Multi-line with drift markers | Rolling 24-month factor loadings over time, drift events marked with red dotted vertical lines |

**Visual language constants:**
- Background: `#0E1117` (matches HF Spaces dark mode)
- Factor colors: blue (Mkt-RF), orange (SMB), green (HML), red (RMW), purple (CMA), yellow (Mom)
- Drift markers: red dotted vertical lines
- Non-significant factor bars: 35% opacity

**Note:** Visual polish (title spacing, margins, font sizes, legend positioning) deferred to week 10 polish phase.

**Validation results (ARKK):**
- All three charts rendered cleanly with real data.
- NAV chart JSON: 9,016 chars. Loadings chart: 8,383 chars. Rolling chart: 23,134 chars.
- HTML test outputs visually inspected and confirmed correct.

### Commits (Week 4)

| Hash | Message |
|---|---|
| 99b4572 | Week 4: fund metadata fetcher with hardcoded universe and FMP fallback |
| 18561f2 | Week 4: chart generator with NAV, factor loadings, and rolling exposure charts |
| b9bbd66 | Remove test chart outputs from tracking |

---

## Open Issues and Decisions Pending

| Item | Status |
|---|---|
| Ken French data refresh frequency | Currently manual (`refresh=True`). Automated refresh cadence deferred to post-launch. |
| Visual polish (spacing, margins, fonts) | Deferred to week 10 polish phase. |
| FMP metadata upgrade | FMP Starter tier 403s on ETF info endpoint. Hardcoded table used for v1. Upgrade to higher tier in v1.1 if needed. |

---

## Architecture Decisions Logged

- **Single agent, fresh tool surface.** No reuse of Demo 1 stack. Seven new tools (6 complete, agent loop pending).
- **Orchestrator:** Claude Agent SDK.
- **Brain:** Claude Sonnet for reasoning and interpretation. Haiku for cheap intermediate steps where appropriate.
- **Factor model:** Fama-French 6 (FF5 + Momentum). Custom 7-factor model deferred to v1.1.
- **Drift detection:** Rolling 24-month window, 1-month step, flag at 1.5 standard deviations. Minimum 12 prior windows before flagging. CUSUM/Bayesian change-point detection deferred to v1.1.
- **Confidence scoring:** Multi-dimensional vector (r-squared, t-stat strength, sample adequacy, factor stability). Each dimension reported separately. No single collapsed score.
- **Data source for factors:** Ken French data library (free, monthly updates). Not computed internally.
- **Caching strategy:** Local CSV cache in `data/french_factors/`. Avoids repeated downloads. `refresh=True` flag for manual cache busting.
- **Fund metadata:** Hardcoded lookup table for 34-fund universe. FMP profile fallback for unknown tickers. Last resort returns ticker with nulls.
- **Chart output format:** Plotly figures serialized to JSON strings. Deserialized in Gradio UI for rendering.

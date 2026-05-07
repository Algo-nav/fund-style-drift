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

---

## Week 1 — Remaining (In Progress)

| Track | Goal | Status |
|---|---|---|
| Track 1 | Ken French FF6 data pipeline | Complete |
| Track 2 | ETF price data via yfinance, monthly returns, single OLS regression in notebook | Pending |
| Track 3 | Mutual fund NAV validation (yfinance/FMP), N-PORT XML parsing on 1 fund | Pending |

---

## Open Issues and Decisions Pending

| Item | Status |
|---|---|
| yfinance mutual fund NAV coverage | Unverified. Track 3 risk canary. |
| FMP Starter tier mutual fund metadata coverage | Unverified. Track 3. |
| N-PORT XML parsing feasibility | Unverified. Track 3. |
| Fund universe final list (30-40 funds) | Deferred to after Track 3 confirms mutual fund viability. |
| Plotly version and theme to match Demo 1 visual language | Deferred to chart generator build. |
| Ken French data refresh frequency | Currently manual (`refresh=True`). Automated refresh cadence to be decided in week 2+. |

---

## Architecture Decisions Logged

- **Single agent, fresh tool surface.** No reuse of Demo 1 stack. Seven new tools.
- **Orchestrator:** Claude Agent SDK.
- **Brain:** Claude Sonnet for reasoning and interpretation. Haiku for cheap intermediate steps where appropriate.
- **Factor model:** Fama-French 6 (FF5 + Momentum). Custom 7-factor model deferred to v1.1.
- **Drift detection:** Rolling 24-month window, 1-month step, flag at 1.5 standard deviations. CUSUM/Bayesian change-point detection deferred to v1.1.
- **Confidence scoring:** Multi-dimensional vector (r-squared, t-stat strength, sample adequacy, factor stability). Each dimension reported separately. No single collapsed score.
- **Data source for factors:** Ken French data library (free, monthly updates). Not computed internally.
- **Caching strategy:** Local CSV cache in `data/french_factors/`. Avoids repeated downloads. `refresh=True` flag for manual cache busting.

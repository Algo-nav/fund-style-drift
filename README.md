---
title: Fund Style Drift Detector
emoji: 📊
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.14.0
app_file: app.py
pinned: false
license: mit
short_description: FF6 factor regression detects style drift in US funds
---

# Fund Style Drift Detector

**Rolling Fama-French 6-factor analysis across 33 US equity funds. Detects statistically significant shifts in factor exposures over time.**

Built by [Navneet Danturi](https://linkedin.com/in/navneet-danturi/) · [GitHub](https://github.com/Algo-nav/fund-style-drift) · [Hugging Face](https://huggingface.co/Nav772)

---

## What This Does

Style drift is when a fund's actual investment behavior diverges from its stated mandate. A "value" fund that quietly shifted toward growth stocks. A "small-cap" fund whose holdings crept toward large-cap. These shifts are real, they happen gradually, and they are rarely announced.

This tool detects them quantitatively.

For each of 33 US equity funds (ETFs and mutual funds), the system runs rolling Fama-French 6-factor OLS regressions on 7 years of monthly return data (2019-2025). Each regression window is 24 months, stepping forward 1 month at a time. The result is a time series of factor exposures per fund - and a statistical flag when any exposure moves significantly away from its historical baseline.

Every finding comes with a multi-dimensional confidence assessment. No single collapsed "confidence score." Four honest dimensions, reported separately.

---

## Fund Universe (33 Funds)

**ETFs (20):** SPY, VOO, QQQ, IWM, SPYG, SPYV, VTV, VUG, MTUM, QUAL, USMV, SPLV, VYM, DGRO, ARKK, ARKG, XLK, XLF, XLE, XLV

**Mutual Funds (13):** VFINX, VWUSX, FCNTX, FXAIX, AGTHX, AIVSX, PRGFX, PRFDX, MFEKX, LMOPX, CGMFX, SEQUX, DODGX

Coverage spans large-cap blend, growth, value, small-cap, momentum, quality, low volatility, dividend, sector, and actively managed funds.

---

## Factor Model

The Fama-French 6-factor model extends the original 3-factor model with profitability, investment, and momentum factors:

```
R_fund - R_f = α + β₁(Mkt-RF) + β₂(SMB) + β₃(HML) + β₄(RMW) + β₅(CMA) + β₆(Mom) + ε
```

| Factor | Full Name | What It Captures |
|---|---|---|
| Mkt-RF | Market minus risk-free | Broad equity market exposure |
| SMB | Small minus big | Tilt toward small-cap stocks |
| HML | High minus low | Tilt toward value stocks |
| RMW | Robust minus weak | Tilt toward profitable companies |
| CMA | Conservative minus aggressive | Tilt toward low-investment companies |
| Mom | Momentum | Tilt toward recent winners |

Factor data sourced from the [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) at Dartmouth. Free, monthly updates, authoritative.

---

## Drift Detection Methodology

### Rolling Window Regression

A single full-period regression produces one set of factor loadings representing average behavior over the entire history. It cannot detect when behavior changed.

Rolling window regression solves this by running the same regression repeatedly on overlapping subsets:

```
Window 1:  months 1-24   → loadings set 1
Window 2:  months 2-25   → loadings set 2
...
Window 61: months 61-84  → loadings set 61
```

With 84 months of data (2019-2025) and a 24-month window stepping 1 month at a time, each fund produces 61 regression results. Plotting factor loadings across windows gives a time series of factor exposures.

**Window size choice (24 months):** Balances statistical reliability (enough observations per regression) against sensitivity (short enough to catch drift within 2 years). Fewer than 24 months produces unreliable OLS estimates with 6 factors. More than 36 months smooths over real drift events.

### Drift Flagging

Drift is flagged when a factor loading in the current window is more than **1.5 standard deviations** from the mean of all prior windows for that factor.

```
z_score = (current_loading - historical_mean) / historical_std
flag if |z_score| >= 1.5
```

**Threshold choice (1.5σ):** Deliberately sits between 1σ (too noisy, flags normal variation) and 2σ (too conservative, misses gradual drift). The minimum history requirement of 12 prior windows before flagging prevents false positives during the warm-up period.

**What a drift event tells you:** Not that the fund is doing something wrong - that its systematic factor exposure has shifted measurably relative to its own history. Whether that matters depends on the fund's mandate and the investor's expectations.

---

## Confidence Assessment

Most AI-generated analysis collapses uncertainty into a single number ("confidence: 87%"). That number is meaningless without knowing what it measures.

This system reports four independent dimensions, each with its underlying metric:

| Dimension | Metric | Thresholds |
|---|---|---|
| **Fit** | Adjusted R-squared | High ≥0.70, Moderate 0.40-0.70, Low <0.40 |
| **Significance** | Count of factors with abs(t-stat) ≥2.0 | High 4+, Moderate 2-3, Low 0-1 |
| **Sample** | Number of monthly observations | Adequate 36+, Marginal 24-35, Insufficient <24 |
| **Normality** | Jarque-Bera p-value on residuals | Pass ≥0.05, Flag <0.05 |

Adjusted R-squared penalizes for the number of factors, preventing overfitting inflation. The Jarque-Bera test flags when OLS assumptions about residual normality are violated - which affects the reliability of t-statistics used in the Significance dimension.

No dimension is more important than the others. A high-fit, low-significance result tells a different story than a moderate-fit, high-significance result. Both matter.

---

## Technical Architecture

### Stack

| Component | Tool | Why |
|---|---|---|
| Factor data | Ken French Data Library | Free, authoritative, monthly updates |
| Fund prices/NAV | yfinance | Reliable monthly data for ETFs and mutual funds |
| Holdings data | SEC EDGAR N-PORT | Quarterly holdings filings, machine-readable XML |
| OLS regression | statsmodels | Full regression diagnostics, residual tests |
| Residual diagnostics | scipy.stats | Jarque-Bera normality test |
| Narrative generation | Claude Sonnet (claude-sonnet-4-6) | Plain-English interpretation of quantitative results |
| Charts | Plotly | Interactive, dark-mode native |
| UI | Gradio 6.14 | Gallery + live regen pattern |
| Data validation | Pydantic | Input/output schemas on every tool |

### Agent Architecture

Claude is the interpreter, not the researcher. All quantitative computation happens in Python:

```
ticker
  → fund_metadata_fetcher      (name, AUM, expense ratio, inception)
  → french_factor_fetcher      (FF6 monthly factors, cached locally)
  → fund_price_fetcher         (monthly returns, missing month check)
  → factor_regression_engine   (full-period OLS + 4 confidence dimensions)
  → drift_detection_engine     (rolling OLS + drift event flagging)
  → nport_parser               (latest N-PORT holdings from EDGAR)
  → chart_generator            (3 Plotly charts as JSON)
  → Claude Sonnet              (plain-English narrative, 4 sections)
```

Claude receives the completed quantitative results and writes a structured narrative: Fund Snapshot, Factor Profile, Style Drift Analysis, Confidence Assessment. It does not recompute anything.

### Performance Optimizations

**Cache-first factor data:** Ken French CSV files are downloaded once and cached locally as CSV. Subsequent runs read from disk. A `refresh=True` flag forces re-download. This eliminates ~2 seconds of network latency per agent run.

**Pre-generated gallery:** All 33 fund reports are generated offline and stored as JSON (~77KB each). The gallery tab loads instantly from disk - no API calls, no latency. Only the Live Regen tab triggers live computation.

**Cumulative return index:** The NAV chart displays a base-100 cumulative return index rather than raw prices. This makes funds with different price levels directly comparable on the same visual scale.

**Pydantic validation throughout:** Every tool has typed input and output schemas. Validation failures surface early, before they propagate into regression or chart generation errors.

**Structured error handling:** Every tool returns a partial result with an `error` field rather than raising exceptions. The agent loop continues even when individual tools fail (N-PORT holdings, for example, fail silently for some ETF structures without blocking report generation).

### N-PORT ETF Parsing

Mutual funds file N-PORT directly under their own CIK. ETFs are structured differently - they file under trust entities (e.g. ARKK files under "ARK ETF Trust", not under the ARKK ticker). Standard EDGAR CIK lookup by ticker fails for this structure.

Fix: hardcoded CIK override table for all 20 ETFs in the universe, mapped to their trust entity CIKs. Mutual funds use dynamic lookup via the EDGAR company search atom feed.

---

## Research References

The factor model and methodology are grounded in academic literature:

**Fama, E.F. & French, K.R. (1993).** Common risk factors in the returns on stocks and bonds. *Journal of Financial Economics, 33*(1), 3-56. The original 3-factor model (market, size, value).

**Fama, E.F. & French, K.R. (2015).** A five-factor asset pricing model. *Journal of Financial Economics, 116*(1), 1-22. Adds profitability (RMW) and investment (CMA) to the 3-factor model.

**Carhart, M.M. (1997).** On persistence in mutual fund performance. *Journal of Finance, 52*(1), 57-82. Adds momentum to the Fama-French 3-factor model.

**Sharpe, W.F. (1992).** Asset allocation: Management style and performance measurement. *Journal of Portfolio Management, 18*(2), 7-19. Returns-based style analysis - the methodological ancestor of factor regression for fund classification.

---

## UI

Two tabs:

**Gallery:** Pre-generated reports for all 33 funds. Select from the sidebar dropdown. Loads instantly.

**Live Regen:** Run the full pipeline on any supported fund ticker. Expect 30-60 seconds. Returns the same report format as the gallery.

Both tabs render: sidebar fund info + confidence badges, NAV chart (cumulative return index, base 100), factor loadings bar chart (significant factors fully opaque, non-significant dimmed), rolling factor exposures line chart (with drift event markers), Claude-generated narrative, and top holdings table from the most recent N-PORT filing.

---

## Limitations (v1)

- US-listed equity funds only. No bond, balanced, or international funds.
- Factor data ends at 2025-12. Reports will not update automatically.
- N-PORT holdings unavailable for 4 Vanguard ETFs (VOO, VTV, VUG, VYM) due to trust entity filing structure.
- Rolling window drift detection uses fixed thresholds. CUSUM and Bayesian change-point detection deferred to v1.1.
- Fund universe is fixed at 33 funds. Custom fund coverage via Live Regen tab for any supported ticker.

---

## Author

**Navneet Danturi** - Data Scientist and GenAI Engineer based in Bangkok, Thailand. Building AI agents for finance document intelligence.

- LinkedIn: [linkedin.com/in/navneet-danturi](https://linkedin.com/in/navneet-danturi/)
- Hugging Face: [huggingface.co/Nav772](https://huggingface.co/Nav772)
- GitHub: [github.com/Algo-nav](https://github.com/Algo-nav)

---

*Factor data: Ken French Data Library (Dartmouth). Holdings data: SEC EDGAR. Price data: Yahoo Finance via yfinance. This tool is for analytical and educational purposes only. Not investment advice.*

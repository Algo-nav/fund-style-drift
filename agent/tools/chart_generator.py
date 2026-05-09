# agent/tools/chart_generator.py

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Visual language constants - consistent across all charts
COLORS = {
    "market":     "#4F8EF7",   # blue - Mkt-RF
    "size":       "#F7A84F",   # orange - SMB
    "value":      "#4FD18B",   # green - HML
    "profit":     "#F76F6F",   # red - RMW
    "invest":     "#A084E8",   # purple - CMA
    "momentum":   "#F7E24F",   # yellow - Mom
    "drift":      "#FF4444",   # red markers for drift events
    "background": "#0E1117",   # dark background matching HF Spaces dark mode
    "surface":    "#1A1D27",   # card surface
    "text":       "#FAFAFA",   # primary text
    "subtext":    "#A0A0B0",   # secondary text
    "grid":       "#2A2D3A",   # grid lines
}

FACTOR_COLORS = {
    "Mkt-RF": COLORS["market"],
    "SMB":    COLORS["size"],
    "HML":    COLORS["value"],
    "RMW":    COLORS["profit"],
    "CMA":    COLORS["invest"],
    "Mom":    COLORS["momentum"],
}

FACTOR_LABELS = {
    "Mkt-RF": "Market (Mkt-RF)",
    "SMB":    "Size (SMB)",
    "HML":    "Value (HML)",
    "RMW":    "Profitability (RMW)",
    "CMA":    "Investment (CMA)",
    "Mom":    "Momentum (Mom)",
}


class ChartInput(BaseModel):
    ticker: str
    fund_name: str

    # For NAV chart - monthly prices {"YYYY-MM": price}
    monthly_prices: dict

    # For factor loading bar chart - single regression result
    factor_loadings: dict    # {factor: loading}
    factor_tstats: dict      # {factor: t_stat}

    # For rolling exposure chart - from drift detection engine
    # List of {date, factor_loadings, adj_r_squared}
    rolling_windows: list

    # Drift events for markers - list of {date, factor, z_score, direction}
    drift_events: list


class ChartOutput(BaseModel):
    nav_chart_json: str         # Plotly figure as JSON string
    loadings_chart_json: str    # Plotly figure as JSON string
    rolling_chart_json: str     # Plotly figure as JSON string
    error: Optional[str] = None


def _apply_dark_theme(fig: go.Figure, title: str) -> go.Figure:
    """Apply consistent dark theme to any figure."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=COLORS["text"], size=14),
            x=0.0,
            xanchor="left"
        ),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"], size=11),
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["grid"],
            borderwidth=1,
            font=dict(color=COLORS["text"], size=10)
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            linecolor=COLORS["grid"],
            tickfont=dict(color=COLORS["subtext"])
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            linecolor=COLORS["grid"],
            tickfont=dict(color=COLORS["subtext"])
        )
    )
    return fig


def build_nav_chart(ticker: str, fund_name: str, monthly_prices: dict) -> go.Figure:
    """
    Line chart of monthly NAV/price over the full history.
    Simple and clean - shows the fund's price trajectory.
    """
    dates = list(monthly_prices.keys())
    prices = list(monthly_prices.values())

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode="lines",
        name="NAV",
        line=dict(color=COLORS["market"], width=2),
        fill="tozeroy",
        fillcolor="rgba(79, 142, 247, 0.08)"
    ))

    fig = _apply_dark_theme(fig, f"{ticker} - Price History")
    fig.update_layout(
        yaxis_title="Price (USD)",
        xaxis_title=None,
        showlegend=False,
        height=300
    )

    return fig


def build_loadings_chart(
    ticker: str,
    factor_loadings: dict,
    factor_tstats: dict
) -> go.Figure:
    """
    Horizontal bar chart of current factor loadings.
    Significant factors (abs t-stat >= 2.0) are fully opaque.
    Non-significant factors are dimmed.
    """
    factors = list(FACTOR_LABELS.keys())
    loadings = [factor_loadings.get(f, 0.0) for f in factors]
    tstats = [factor_tstats.get(f, 0.0) for f in factors]
    labels = [FACTOR_LABELS[f] for f in factors]
    colors = [FACTOR_COLORS[f] for f in factors]

    # Dim non-significant bars
    opacities = [1.0 if abs(t) >= 2.0 else 0.35 for t in tstats]
    bar_colors = []
    for c, op in zip(colors, opacities):
        if op < 1.0:
            # Convert hex to rgba with reduced opacity
            r = int(c[1:3], 16)
            g = int(c[3:5], 16)
            b = int(c[5:7], 16)
            bar_colors.append(f"rgba({r},{g},{b},{op})")
        else:
            bar_colors.append(c)

    # Custom hover text
    hover_texts = []
    for f, l, t in zip(factors, loadings, tstats):
        sig = "significant" if abs(t) >= 2.0 else "not significant"
        hover_texts.append(f"{FACTOR_LABELS[f]}<br>Loading: {l:.4f}<br>t-stat: {t:.2f} ({sig})")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=loadings,
        y=labels,
        orientation="h",
        marker_color=bar_colors,
        hovertext=hover_texts,
        hoverinfo="text",
        text=[f"{l:.3f}" for l in loadings],
        textposition="outside",
        textfont=dict(color=COLORS["text"], size=10)
    ))

    # Zero line
    fig.add_vline(x=0, line_color=COLORS["subtext"], line_width=1)

    fig = _apply_dark_theme(fig, f"{ticker} - Factor Loadings (Full Period)")
    fig.update_layout(
        xaxis_title="Factor Loading",
        yaxis_title=None,
        height=350,
        xaxis=dict(
            gridcolor=COLORS["grid"],
            linecolor=COLORS["grid"],
            tickfont=dict(color=COLORS["subtext"]),
            zeroline=False
        )
    )

    return fig


def build_rolling_chart(
    ticker: str,
    rolling_windows: list,
    drift_events: list,
    factors_to_show: list = None
) -> go.Figure:
    """
    Line chart of rolling factor exposures over time.
    Each factor is one line. Drift events are marked with vertical lines.
    Default: show all 6 factors. Can be filtered to a subset.
    """
    if factors_to_show is None:
        factors_to_show = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]

    # Build time series per factor from rolling windows
    dates = [w["date"] for w in rolling_windows]
    factor_series = {f: [] for f in factors_to_show}

    for w in rolling_windows:
        for f in factors_to_show:
            factor_series[f].append(w["factor_loadings"].get(f, None))

    fig = go.Figure()

    # One line per factor
    for f in factors_to_show:
        fig.add_trace(go.Scatter(
            x=dates,
            y=factor_series[f],
            mode="lines",
            name=FACTOR_LABELS[f],
            line=dict(color=FACTOR_COLORS[f], width=1.5),
            hovertemplate=f"{FACTOR_LABELS[f]}: %{{y:.4f}}<br>%{{x}}<extra></extra>"
        ))

    # Drift event markers - vertical lines at drift dates
    # Deduplicate dates (multiple factors can drift on same date)
    drift_dates = list(set(e["date"] for e in drift_events))
    for d in drift_dates:
        fig.add_vline(
            x=d,
            line_color=COLORS["drift"],
            line_width=1,
            line_dash="dot",
            opacity=0.6
        )

    # Add a single invisible trace for the drift legend entry
    if drift_dates:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            name="Drift flagged",
            line=dict(color=COLORS["drift"], width=1, dash="dot"),
            showlegend=True
        ))

    # Zero reference line
    fig.add_hline(y=0, line_color=COLORS["subtext"], line_width=0.5)

    fig = _apply_dark_theme(fig, f"{ticker} - Rolling Factor Exposures (24-Month Window)")
    fig.update_layout(
        yaxis_title="Factor Loading",
        xaxis_title=None,
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig


def generate_charts(inp: ChartInput) -> ChartOutput:
    try:
        # Build all three charts
        nav_fig = build_nav_chart(
            ticker=inp.ticker,
            fund_name=inp.fund_name,
            monthly_prices=inp.monthly_prices
        )

        loadings_fig = build_loadings_chart(
            ticker=inp.ticker,
            factor_loadings=inp.factor_loadings,
            factor_tstats=inp.factor_tstats
        )

        rolling_fig = build_rolling_chart(
            ticker=inp.ticker,
            rolling_windows=inp.rolling_windows,
            drift_events=inp.drift_events
        )

        return ChartOutput(
            nav_chart_json=nav_fig.to_json(),
            loadings_chart_json=loadings_fig.to_json(),
            rolling_chart_json=rolling_fig.to_json(),
            error=None
        )

    except Exception as e:
        return ChartOutput(
            nav_chart_json="{}",
            loadings_chart_json="{}",
            rolling_chart_json="{}",
            error=str(e)
        )


if __name__ == "__main__":
    # Pull real data and render charts for ARKK
    from agent.tools.french_factor_fetcher import get_french_factors, FrenchFactorInput
    from agent.tools.fund_price_fetcher import get_fund_returns, FundPriceInput
    from agent.tools.factor_regression_engine import run_factor_regression, FactorRegressionInput
    from agent.tools.drift_detection_engine import detect_drift, DriftDetectionInput

    ticker = "ARKK"
    start = "2019-01"
    end = "2025-12"

    print(f"Fetching data for {ticker}...")
    factors = get_french_factors(FrenchFactorInput(start_date=start, end_date=end))
    prices = get_fund_returns(FundPriceInput(ticker=ticker, start_date=start, end_date=end))

    print("Running regression...")
    regression = run_factor_regression(FactorRegressionInput(
        ticker=ticker,
        returns=prices.returns,
        factors=factors.factors,
        start_date=start,
        end_date=end
    ))

    print("Running drift detection...")
    drift = detect_drift(DriftDetectionInput(
        ticker=ticker,
        returns=prices.returns,
        factors=factors.factors,
        start_date=start,
        end_date=end
    ))

    print("Generating charts...")
    charts = generate_charts(ChartInput(
        ticker=ticker,
        fund_name="ARK Innovation ETF",
        monthly_prices=prices.returns,   # using returns as proxy for now
        factor_loadings=regression.factor_loadings,
        factor_tstats=regression.factor_tstats,
        rolling_windows=[w.model_dump() for w in drift.rolling_windows],
        drift_events=[e.model_dump() for e in drift.drift_events]
    ))

    print(f"Error: {charts.error}")
    print(f"NAV chart JSON length: {len(charts.nav_chart_json)}")
    print(f"Loadings chart JSON length: {len(charts.loadings_chart_json)}")
    print(f"Rolling chart JSON length: {len(charts.rolling_chart_json)}")

    # Save charts to outputs/ for visual inspection
    import plotly.io as pio
    import os

    os.makedirs("outputs", exist_ok=True)

    for name, json_str in [
        ("nav", charts.nav_chart_json),
        ("loadings", charts.loadings_chart_json),
        ("rolling", charts.rolling_chart_json)
    ]:
        fig = pio.from_json(json_str)
        path = f"outputs/test_{ticker}_{name}.html"
        fig.write_html(path)
        print(f"Saved: {path}")

    print("\nOpen the HTML files in your browser to inspect the charts.")
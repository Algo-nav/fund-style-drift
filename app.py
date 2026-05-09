# app.py

import gradio as gr
import json
import plotly.io as pio
from pathlib import Path
from agent.agent import run_agent

REPORTS_DIR = Path("outputs/reports")

FUND_UNIVERSE = sorted([
    "ARKK", "ARKG", "DGRO", "DODGX", "FCNTX", "FXAIX",
    "AGTHX", "AIVSX", "IWM", "LMOPX", "MFEKX", "MTUM",
    "PRGFX", "PRFDX", "QUAL", "QQQ", "SEQUX", "CGMFX",
    "SPY", "SPYG", "SPYV", "SPLV", "USMV", "VOO",
    "VTV", "VUG", "VFINX", "VWUSX", "VYM", "XLF",
    "XLK", "XLE", "XLV"
])

CUSTOM_CSS = """
@import url('https://fonts.cdnfonts.com/css/playfair-display');
@import url('https://fonts.cdnfonts.com/css/ibm-plex-sans');
@import url('https://fonts.cdnfonts.com/css/ibm-plex-mono');

:root {
    --font-display: 'Playfair Display', Georgia, serif;
    --font-body: 'IBM Plex Sans', system-ui, sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;

    --accent: #C9A84C;
    --accent-dim: rgba(201, 168, 76, 0.15);
    --accent-border: rgba(201, 168, 76, 0.4);
    --radius: 6px;
    --transition: 0.2s ease;
}

/* ── Light mode ── */
:root, .light {
    --bg-primary: #F7F5F0;
    --bg-secondary: #EDEAE2;
    --bg-card: #FFFFFF;
    --bg-sidebar: #F0EDE6;
    --text-primary: #1A1814;
    --text-secondary: #5C5648;
    --text-muted: #8C8478;
    --border: rgba(0,0,0,0.1);
    --shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* ── Dark mode ── */
.dark {
    --bg-primary: #0F0E0C;
    --bg-secondary: #181610;
    --bg-card: #1C1A16;
    --bg-sidebar: #161410;
    --text-primary: #F0EDE6;
    --text-secondary: #A89F8C;
    --text-muted: #6B6456;
    --border: rgba(255,255,255,0.07);
    --shadow: 0 2px 16px rgba(0,0,0,0.4);
}

body, .gradio-container {
    font-family: var(--font-body) !important;
    background: var(--bg-primary) !important;
}

/* ── Hero header ── */
.hero-block {
    background: linear-gradient(135deg, #0D1B2A 0%, #1A2F45 50%, #0D1B2A 100%);
    padding: 36px 48px 28px;
    border-bottom: 2px solid var(--accent);
    position: relative;
    overflow: hidden;
}

.hero-block::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        90deg,
        transparent,
        transparent 80px,
        rgba(201,168,76,0.03) 80px,
        rgba(201,168,76,0.03) 81px
    );
    pointer-events: none;
}

.hero-title {
    font-family: var(--font-display) !important;
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    color: #F0EDE6 !important;
    margin: 0 0 6px 0 !important;
    letter-spacing: -0.02em;
    line-height: 1.15;
}

.hero-sub {
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    color: var(--accent) !important;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 0 !important;
}

/* ── Sidebar ── */
.sidebar-wrap {
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    padding: 0;
    height: 100%;
}

.sidebar-section {
    padding: 20px 20px 16px;
    border-bottom: 1px solid var(--border);
}

.sidebar-label {
    font-family: var(--font-mono) !important;
    font-size: 0.65rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted) !important;
    margin: 0 0 12px 0 !important;
}

.fund-name-display {
    font-family: var(--font-display) !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 0 10px 0 !important;
    line-height: 1.3;
}

.meta-row {
    font-size: 0.8rem !important;
    color: var(--text-secondary) !important;
    margin: 4px 0 !important;
    line-height: 1.5;
}

.meta-row strong {
    color: var(--text-primary) !important;
    font-weight: 500;
}

.conf-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.78rem !important;
}

.conf-row:last-child { border-bottom: none; }

.conf-label {
    color: var(--text-muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
}

.conf-badge {
    font-weight: 600;
    font-size: 0.7rem !important;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: var(--font-mono) !important;
}

.badge-high    { background: rgba(74,222,128,0.15) !important; color: #4ADE80 !important; border: 1px solid rgba(74,222,128,0.3) !important; }
.badge-moderate { background: rgba(251,191,36,0.15) !important; color: #FBBF24 !important; border: 1px solid rgba(251,191,36,0.3) !important; }
.badge-low     { background: rgba(248,113,113,0.15) !important; color: #F87171 !important; border: 1px solid rgba(248,113,113,0.3) !important; }
.badge-adequate { background: rgba(74,222,128,0.15) !important; color: #4ADE80 !important; border: 1px solid rgba(74,222,128,0.3) !important; }
.badge-marginal { background: rgba(251,191,36,0.15) !important; color: #FBBF24 !important; border: 1px solid rgba(251,191,36,0.3) !important; }
.badge-insufficient { background: rgba(248,113,113,0.15) !important; color: #F87171 !important; border: 1px solid rgba(248,113,113,0.3) !important; }
.badge-pass    { background: rgba(74,222,128,0.15) !important; color: #4ADE80 !important; border: 1px solid rgba(74,222,128,0.3) !important; }
.badge-flag    { background: rgba(248,113,113,0.15) !important; color: #F87171 !important; border: 1px solid rgba(248,113,113,0.3) !important; }

/* ── Main panel ── */
.main-panel {
    background: var(--bg-primary);
    padding: 24px 32px;
}

/* ── Dropdown ── */
.gr-dropdown, select, .wrap {
    font-family: var(--font-body) !important;
    border-radius: var(--radius) !important;
}

/* ── Tabs ── */
.tab-nav button {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Charts ── */
.gr-plot {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
    margin-bottom: 16px !important;
}

/* ── Narrative ── */
.narrative-block h2 {
    font-family: var(--font-display) !important;
    font-size: 1.3rem !important;
    color: var(--text-primary) !important;
    margin-bottom: 16px !important;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--accent-border);
}

.narrative-block p {
    font-size: 0.88rem !important;
    line-height: 1.75 !important;
    color: var(--text-secondary) !important;
    margin-bottom: 12px !important;
}

.narrative-block h3 {
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent) !important;
    margin: 20px 0 8px !important;
}

/* ── Holdings table ── */
.holdings-block table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem !important;
}

.holdings-block th {
    font-family: var(--font-mono) !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted) !important;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
}

.holdings-block td {
    padding: 7px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary) !important;
}

.holdings-block tr:last-child td { border-bottom: none; }

/* ── Methodology ── */
.method-block {
    font-family: var(--font-mono) !important;
    font-size: 0.68rem !important;
    color: var(--text-muted) !important;
    line-height: 1.6;
    padding: 16px 0;
    border-top: 1px solid var(--border);
}

/* ── Status message ── */
.status-msg {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    color: var(--accent) !important;
    padding: 8px 0;
}

/* ── Sidebar scrollable ── */
aside {
    overflow-y: auto !important;
}

/* ── Input & button ── */
input[type=text], .gr-textbox textarea {
    font-family: var(--font-mono) !important;
    font-size: 0.82rem !important;
    border-radius: var(--radius) !important;
}

button.primary {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: var(--accent) !important;
    color: #0F0E0C !important;
    border-radius: var(--radius) !important;
}

/* ── Section divider ── */
.section-divider {
    height: 1px;
    background: var(--border);
    margin: 24px 0;
}
"""

HERO_HTML = """
<div class="hero-block">
    <h1 class="hero-title">Fund Style Drift Detector</h1>
    <p class="hero-sub">Rolling Fama-French 6-factor analysis across 33 US equity funds. Detects statistically significant shifts in factor exposures over time.</p>
    <p class="hero-sub" style="margin-top:6px;opacity:0.7">Claude &nbsp;+&nbsp; Ken French &nbsp;+&nbsp; SEC EDGAR &nbsp;+&nbsp; yFinance</p>
</div>
"""


def load_report(ticker: str) -> dict | None:
    path = REPORTS_DIR / f"{ticker}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def format_aum(aum: float | None) -> str:
    if aum is None:
        return "N/A"
    if aum >= 1_000_000_000:
        return f"${aum / 1_000_000_000:.1f}B"
    if aum >= 1_000_000:
        return f"${aum / 1_000_000:.0f}M"
    return f"${aum:,.0f}"


def json_to_fig(json_str: str):
    if not json_str or json_str == "{}":
        return None
    try:
        return pio.from_json(json_str)
    except Exception:
        return None


def badge(label: str) -> str:
    cls = f"badge-{label.lower()}" if label else "badge-low"
    return f'<span class="conf-badge {cls}">{label.upper()}</span>'


def render_sidebar(meta: dict, regression: dict) -> tuple:
    fund_name = meta.get("name", "")
    category = meta.get("category") or "N/A"
    aum = format_aum(meta.get("aum_usd"))
    expense = f"{meta.get('expense_ratio', 0) * 100:.2f}%" if meta.get("expense_ratio") else "N/A"
    inception = meta.get("inception_date") or "N/A"

    fund_name_html = f'<p class="fund-name-display">{fund_name}</p>'
    meta_html = (
        f'<p class="meta-row"><strong>Category</strong> &nbsp; {category}</p>'
        f'<p class="meta-row"><strong>AUM</strong> &nbsp; {aum}</p>'
        f'<p class="meta-row"><strong>Expense Ratio</strong> &nbsp; {expense}</p>'
        f'<p class="meta-row"><strong>Inception</strong> &nbsp; {inception}</p>'
    )

    conf_fit = regression.get("conf_fit", {})
    conf_sig = regression.get("conf_significance", {})
    conf_sample = regression.get("conf_sample", {})
    conf_norm = regression.get("conf_normality", {})

    conf_html = f"""
    <div class="conf-row">
        <span class="conf-label">Fit</span>
        {badge(conf_fit.get('label',''))}
    </div>
    <div class="conf-row">
        <span class="conf-label">Significance</span>
        {badge(conf_sig.get('label',''))}
    </div>
    <div class="conf-row">
        <span class="conf-label">Sample</span>
        {badge(conf_sample.get('label',''))}
    </div>
    <div class="conf-row">
        <span class="conf-label">Normality</span>
        {badge(conf_norm.get('label',''))}
    </div>
    <div style="margin-top:12px; font-size:0.72rem; color:var(--text-muted); font-family:var(--font-mono)">
        Adj R²={conf_fit.get('metric',0):.3f} &nbsp;|&nbsp;
        {int(conf_sig.get('metric',0))}/6 factors &nbsp;|&nbsp;
        {int(conf_sample.get('metric',0))}mo &nbsp;|&nbsp;
        JB p={conf_norm.get('metric',0):.3f}
    </div>
    """

    return fund_name_html, meta_html, conf_html


def render_report(report: dict):
    if not report:
        return ("", "", "", None, None, None, "", "", "")

    meta = report.get("metadata") or {}
    regression = report.get("regression") or {}
    holdings = report.get("holdings") or {}
    charts = report.get("charts") or {}
    narrative = report.get("narrative") or ""

    fund_name_html, meta_html, conf_html = render_sidebar(meta, regression)

    nav_fig = json_to_fig(charts.get("nav_chart_json"))
    loadings_fig = json_to_fig(charts.get("loadings_chart_json"))
    rolling_fig = json_to_fig(charts.get("rolling_chart_json"))

    top_holdings = holdings.get("top_holdings", [])
    if top_holdings:
        rows = ""
        for i, h in enumerate(top_holdings[:10], 1):
            rows += (
                f"<tr><td>{i}</td>"
                f"<td>{h.get('name','N/A')}</td>"
                f"<td style='text-align:right;font-family:var(--font-mono)'>"
                f"{h.get('pct_weight',0):.2f}%</td></tr>"
            )
        holdings_html = f"""
        <div class="holdings-block">
            <table>
                <thead>
                    <tr><th>#</th><th>Security</th><th style='text-align:right'>Weight</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="font-size:0.7rem;color:var(--text-muted);font-family:var(--font-mono);margin-top:10px">
                As of {holdings.get('period_ending','N/A')} &nbsp;|&nbsp;
                {holdings.get('total_holdings','N/A')} total holdings &nbsp;|&nbsp;
                Top 10 concentration: {holdings.get('top10_concentration',0):.1f}%
            </p>
        </div>
        """
    else:
        holdings_html = '<p style="font-size:0.8rem;color:var(--text-muted);font-family:var(--font-mono)">Holdings data not available for this fund.</p>'

    return (
        fund_name_html, meta_html, conf_html,
        nav_fig, loadings_fig, rolling_fig,
        narrative, holdings_html, ""
    )


def on_gallery_select(ticker: str):
    if not ticker:
        return ("", "", "", None, None, None, "", "", "")
    report = load_report(ticker)
    if not report:
        return ("", "", "", None, None, None, "", "",
                f"No report found for {ticker}.")
    return render_report(report)


def on_live_regen(ticker: str):
    ticker = ticker.strip().upper()
    if not ticker:
        return ("", "", "", None, None, None, "", "",
                "Please enter a ticker symbol.")
    report = run_agent(ticker)
    if report.get("error"):
        return ("", "", "", None, None, None, "", "",
                f"Error: {report['error']}")
    return render_report(report)


with gr.Blocks(
    css=CUSTOM_CSS,
    theme=gr.themes.Base(),
    title="Fund Style Drift Detector"
) as demo:

    gr.HTML(HERO_HTML)

    with gr.Sidebar(elem_classes=["sidebar-wrap"]):

        with gr.Column(elem_classes=["sidebar-section"]):
            gr.HTML('<p class="sidebar-label">Select Fund</p>')
            gallery_dropdown = gr.Dropdown(
                choices=FUND_UNIVERSE,
                value=None,
                label="",
                interactive=True,
                show_label=False
            )

        with gr.Column(elem_classes=["sidebar-section"]):
            gr.HTML('<p class="sidebar-label">Fund Info</p>')
            fund_name_html = gr.HTML("")
            meta_html = gr.HTML("")

        with gr.Column(elem_classes=["sidebar-section"]):
            gr.HTML('<p class="sidebar-label">Confidence Assessment</p>')
            conf_html = gr.HTML("")

    with gr.Column(elem_classes=["main-panel"]):

        status_md = gr.HTML("")

        with gr.Tabs():
            with gr.Tab("Gallery"):
                gr.HTML(
                    '<p style="font-size:0.82rem;color:var(--text-muted);'
                    'font-family:var(--font-mono);margin-bottom:16px">'
                    'Select a fund from the sidebar to load its pre-generated report.</p>'
                )
            with gr.Tab("Live Regen"):
                with gr.Row():
                    live_input = gr.Textbox(
                        placeholder="Enter ticker  e.g.  QQQ  VFINX  ARKK",
                        label="",
                        show_label=False,
                        scale=4
                    )
                    live_btn = gr.Button(
                        "Run Analysis",
                        variant="primary",
                        scale=1
                    )
                gr.HTML(
                    '<p style="font-size:0.72rem;color:var(--text-muted);'
                    'font-family:var(--font-mono);margin-top:8px">'
                    'Runs the full pipeline live. Expect 30-60 seconds. '
                    'Supported: any of the 33 funds in the universe.</p>'
                )

        nav_chart = gr.Plot(label="Price History")
        loadings_chart = gr.Plot(label="Factor Loadings")
        rolling_chart = gr.Plot(label="Rolling Factor Exposures")

        gr.HTML('<div class="section-divider"></div>')
        gr.HTML('<p class="sidebar-label" style="margin-bottom:12px">Analysis</p>')
        narrative_md = gr.Markdown("", elem_classes=["narrative-block"])

        gr.HTML('<div class="section-divider"></div>')
        gr.HTML('<p class="sidebar-label" style="margin-bottom:12px">Top Holdings</p>')
        holdings_html = gr.HTML("")

        gr.HTML("""
        <div class="method-block">
            Methodology: Fama-French 6-factor OLS regression (Mkt-RF, SMB, HML, RMW, CMA, Mom).
            Rolling 24-month windows, 1-month step. Drift flagged at 1.5σ from historical mean.
            Factor data: Ken French Data Library (Dartmouth).
            Holdings: SEC EDGAR N-PORT filings. Returns: Yahoo Finance.
        </div>
        """)

    outputs = [
        fund_name_html, meta_html, conf_html,
        nav_chart, loadings_chart, rolling_chart,
        narrative_md, holdings_html, status_md
    ]

    gallery_dropdown.change(
        fn=on_gallery_select,
        inputs=[gallery_dropdown],
        outputs=outputs
    )

    live_btn.click(
        fn=on_live_regen,
        inputs=[live_input],
        outputs=outputs
    )

    live_input.submit(
        fn=on_live_regen,
        inputs=[live_input],
        outputs=outputs
    )


if __name__ == "__main__":
    demo.launch()
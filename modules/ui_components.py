"""
modules/ui_components.py
Reusable SVKM-branded UI components: KPI cards, progress gauges, breadcrumbs.
SVKM Brand colours: Maroon #7B1C1C, Gold #C9973B, Off-white #FAF7F2
"""
import plotly.graph_objects as go
import streamlit as st

# ── Brand palette ──────────────────────────────────────────────────────────────
MAROON        = "#7B1C1C"
DARK_MAROON   = "#5A1212"
GOLD          = "#C9973B"
LIGHT_GOLD    = "#F0D080"
OFF_WHITE     = "#FAF7F2"
GREY_BG       = "#F4F1EC"
TEXT_DARK     = "#1A1A1A"
TEXT_MID      = "#4A4A4A"
GREEN         = "#2E7D32"
AMBER         = "#E65100"
RED           = "#C62828"
BLUE          = "#1565C0"

STATUS_COLOURS = {
    "complete":    GREEN,
    "inprogress":  AMBER,
    "pending":     RED,
    "rejected":    "#616161",
}

# Plotly template customisation
PLOTLY_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, Arial, sans-serif", color=TEXT_DARK),
    margin=dict(t=48, b=32, l=32, r=24),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    colorway=[MAROON, GOLD, "#3A6186", GREEN, AMBER, "#8E24AA", "#00796B"],
)

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Page background */
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
section[data-testid="stSidebar"] { background: #3D0C0C !important; }
section[data-testid="stSidebar"] * { color: #FAF7F2 !important; }
section[data-testid="stSidebar"] .stRadio label { font-size: 14px !important; }
section[data-testid="stSidebar"] hr { border-color: #7B1C1C !important; }

/* KPI cards */
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 18px 20px 14px 20px;
    border-left: 5px solid #7B1C1C;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-card.gold  { border-left-color: #C9973B; }
.kpi-card.green { border-left-color: #2E7D32; }
.kpi-card.red   { border-left-color: #C62828; }
.kpi-card.blue  { border-left-color: #1565C0; }
.kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
             letter-spacing: .06em; color: #4A4A4A; margin-bottom: 6px; }
.kpi-value { font-size: 30px; font-weight: 700; color: #1A1A1A; line-height: 1; }
.kpi-delta { font-size: 12px; font-weight: 500; margin-top: 4px; }
.kpi-delta.up   { color: #2E7D32; }
.kpi-delta.down { color: #C62828; }
.kpi-delta.neutral { color: #4A4A4A; }

/* Section header */
.section-header {
    font-size: 20px; font-weight: 700; color: #7B1C1C;
    margin: 24px 0 4px 0; border-bottom: 2px solid #F0D080; padding-bottom: 6px;
}

/* Breadcrumb */
.breadcrumb {
    font-size: 12px; color: #4A4A4A; margin-bottom: 20px;
    background: #F4F1EC; border-radius: 6px; padding: 6px 14px;
    display: inline-block;
}
.breadcrumb b { color: #7B1C1C; }

/* Status badge */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing:.03em;
}
.badge-green  { background:#E8F5E9; color:#2E7D32; }
.badge-red    { background:#FFEBEE; color:#C62828; }
.badge-amber  { background:#FFF3E0; color:#E65100; }
.badge-grey   { background:#EEEEEE; color:#616161; }

/* Info banner */
.info-banner {
    background: linear-gradient(135deg, #7B1C1C 0%, #5A1212 100%);
    color: white; border-radius: 12px; padding: 18px 24px;
    margin-bottom: 20px;
}
.info-banner h2 { margin:0; font-size:22px; font-weight:700; }
.info-banner p  { margin:6px 0 0; font-size:13px; opacity:.85; }

/* Tabs */
button[data-baseweb="tab"] { font-size: 13px !important; font-weight: 600 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #7B1C1C !important; }
div[data-baseweb="tab-highlight"] { background-color: #7B1C1C !important; }

/* Expander */
details summary { font-weight: 600; font-size: 13px; color: #7B1C1C; }

/* Overdue row highlight handled via df.style */
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, icon: str = ""):
    st.markdown(
        f"""<div class="info-banner">
            <h2>{icon} {title}</h2>
            <p>{subtitle}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def breadcrumb(*parts: str):
    trail = " &rsaquo; ".join(
        f"<b>{p}</b>" if i == len(parts) - 1 else p
        for i, p in enumerate(parts)
    )
    st.markdown(f'<div class="breadcrumb">{trail}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neutral", accent: str = "maroon"):
    """Renders a custom HTML KPI card. accent: maroon|gold|green|red|blue"""
    cls = "" if accent == "maroon" else accent
    delta_cls = {"up": "up", "down": "down"}.get(delta_dir, "neutral")
    delta_html = f'<div class="kpi-delta {delta_cls}">{delta}</div>' if delta else ""
    st.markdown(
        f"""<div class="kpi-card {cls}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>""",
        unsafe_allow_html=True,
    )


def gauge_chart(value: float, title: str, suffix: str = "%",
                green_threshold: float = 80, amber_threshold: float = 50) -> go.Figure:
    """Circular gauge chart for a single completion percentage."""
    if value >= green_threshold:
        colour = GREEN
    elif value >= amber_threshold:
        colour = AMBER
    else:
        colour = RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 36, "color": TEXT_DARK}},
        title={"text": title, "font": {"size": 13, "color": TEXT_MID}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#ccc"},
            "bar": {"color": colour},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, amber_threshold], "color": "#FFEBEE"},
                {"range": [amber_threshold, green_threshold], "color": "#FFF3E0"},
                {"range": [green_threshold, 100], "color": "#E8F5E9"},
            ],
            "threshold": {
                "line": {"color": DARK_MAROON, "width": 3},
                "thickness": 0.8,
                "value": value,
            },
        },
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 240, "margin": dict(t=32, b=16, l=24, r=24)})
    return fig


def apply_plotly_theme(fig, height: int = 360) -> go.Figure:
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": height})
    return fig

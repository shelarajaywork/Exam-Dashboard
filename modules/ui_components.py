"""
modules/ui_components.py
Theme-adaptive UI components: KPI cards, progress gauges, headers and Plotly styling.
Designed to blend seamlessly with both Light and Dark browser/Streamlit modes.
"""
import plotly.graph_objects as go
import streamlit as st

# ── Standard Accessible Palette (works in both Light & Dark modes) ────────────
BLUE   = "#1f77b4"
GREEN  = "#2ca02c"
AMBER  = "#ff7f0e"
RED    = "#d62728"
PURPLE = "#9467bd"
MAROON = "#8c564b"
GOLD   = "#e377c2"
OFF_WHITE = "#FAF7F2"

# Transparent background layout so charts blend with any theme
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=40, b=30, l=30, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
)

GLOBAL_CSS = """
<style>
/* Subtle card outline for metrics that works in both light and dark modes */
div[data-testid="stMetric"] {
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 8px;
    padding: 12px 16px;
    background-color: rgba(128, 128, 128, 0.05);
}
</style>
"""


def inject_css():
    """Injects minimal theme-adaptive CSS."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, icon: str = ""):
    """Renders a clean, theme-adaptive page header."""
    header_text = f"{icon} {title}".strip()
    st.title(header_text)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def breadcrumb(*parts: str):
    """Renders a clean breadcrumb trail using native caption styling."""
    trail = "  ›  ".join(p for p in parts if p)
    st.caption(f"📁 **Location:** {trail}")


def kpi_card(label: str, value: str, delta: str = "", delta_dir: str = "neutral", accent: str = "default"):
    """
    Renders a native Streamlit metric card that automatically adapts
    its fonts, backgrounds, and delta colours to Light and Dark modes.
    """
    delta_val = delta if delta else None
    delta_color = "normal" if delta_dir == "up" else ("inverse" if delta_dir == "down" else "off")
    st.metric(label=label, value=value, delta=delta_val, delta_color=delta_color)


def gauge_chart(value: float, title: str, suffix: str = "%",
                green_threshold: float = 80, amber_threshold: float = 50) -> go.Figure:
    """Circular gauge chart with transparent background to fit any mode."""
    if value >= green_threshold:
        bar_color = GREEN
    elif value >= amber_threshold:
        bar_color = AMBER
    else:
        bar_color = RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix},
        title={"text": title},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": bar_color},
            "bgcolor": "rgba(128, 128, 128, 0.15)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, amber_threshold], "color": "rgba(214, 39, 40, 0.15)"},
                {"range": [amber_threshold, green_threshold], "color": "rgba(255, 127, 14, 0.15)"},
                {"range": [green_threshold, 100], "color": "rgba(44, 160, 44, 0.15)"},
            ],
        },
    ))
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": 240, "margin": dict(t=30, b=10, l=20, r=20)})
    return fig


def apply_plotly_theme(fig, height: int = 360) -> go.Figure:
    """Applies transparent background and layout settings to blend with Light/Dark themes."""
    fig.update_layout(**{**PLOTLY_LAYOUT, "height": height})
    return fig

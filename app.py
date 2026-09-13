"""
app.py — SVKM CED Exam Dashboard
Main entry point. Handles page routing and sidebar branding.
Actual page content is rendered by modules in the `modules/` package.
"""
import streamlit as st

# ── Page configuration (must be first Streamlit call) ─────────────────────────
st.set_page_config(
    page_title="SVKM CED — Exam Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Import modules AFTER set_page_config ──────────────────────────────────────
from modules.ui_components import inject_css
from modules import evaluation_dashboard, result_analysis

# ── Global styles ─────────────────────────────────────────────────────────────
inject_css()

# ── Sidebar branding (Theme-adaptive: clean in both Light & Dark modes) ─────────
with st.sidebar:
    st.markdown("### 🎓 SVKM CED")
    st.caption("Exam Operations & Intelligence Portal")
    st.divider()

    # Primary navigation
    page = st.radio(
        "Navigation",
        options=["📋  Evaluation Dashboard Details", "📊  Result Analysis"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("🔄 Live sync with Google Drive")

# ── Route to page module ──────────────────────────────────────────────────────
if "Evaluation" in page:
    evaluation_dashboard.render()
else:
    result_analysis.render()
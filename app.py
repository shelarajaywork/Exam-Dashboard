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

# ── Sidebar branding ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:16px 0 8px">
            <div style="font-size:28px;">🎓</div>
            <div style="font-size:15px; font-weight:700; letter-spacing:.04em; color:#F0D080;">
                SVKM CED
            </div>
            <div style="font-size:11px; opacity:.75; margin-top:2px; color:#FAF7F2;">
                Exam Intelligence Portal
            </div>
        </div>
        <hr style="border-color:#7B1C1C; margin:8px 0 14px;">
        """,
        unsafe_allow_html=True,
    )

    # Primary navigation
    page = st.radio(
        "Navigation",
        options=["📋  Evaluation Dashboard Details", "📊  Result Analysis"],
        label_visibility="collapsed",
    )

    st.markdown(
        """
        <hr style="border-color:#7B1C1C; margin:14px 0 10px;">
        <div style="font-size:10px; opacity:.55; color:#FAF7F2; text-align:center;">
            Data refreshes every 5 min &bull; Live · Google Drive
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Route to page module ──────────────────────────────────────────────────────
if "Evaluation" in page:
    evaluation_dashboard.render()
else:
    result_analysis.render()
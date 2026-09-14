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
from modules.drive_utils import get_credentials_info
from modules import evaluation_dashboard, result_analysis

# ── Global styles ─────────────────────────────────────────────────────────────
inject_css()

# ── Check Google Service Account Credentials ───────────────────────────────────
if not get_credentials_info():
    st.error("🔑 Google Service Account Credentials Not Found")
    st.info(
        "To connect your Google Drive to Streamlit Cloud, you need to add your Service Account credentials to the app's Secrets.\n\n"
        "### How to configure in Streamlit Cloud (1 minute):\n"
        "1. In the bottom-right corner of your app, click **Manage app**.\n"
        "2. Click the three vertical dots **⋮** > **Settings** > **Secrets**.\n"
        "3. Paste your Google Service Account configuration into the secrets box.\n"
        "4. Click **Save**. The app will automatically reload with your live Google Drive data."
    )
    st.stop()

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
import io
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Page configuration
st.set_page_config(
    page_title="Executive Operations Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished KPI card styling
st.markdown(
    """
    <style>
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.05);
        border: 1px solid rgba(28, 131, 225, 0.15);
        padding: 15px 20px;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Google Drive API Client Initialization
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@st.cache_resource
def get_drive_service():
    """Initializes Google Drive API service using Streamlit secrets."""
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


@st.cache_data(ttl=600)
def load_data_from_drive(folder_id: str):
    """Fetches and reads the latest tabular file (.csv, .xlsx, or Google Sheet) from the target Drive folder."""
    try:
        service = get_drive_service()

        # Query files inside the target folder
        query = (
            f"'{folder_id}' in parents and trashed = false and "
            "("
            "mimeType = 'text/csv' or "
            "mimeType = 'text/comma-separated-values' or "
            "mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            "mimeType = 'application/vnd.ms-excel' or "
            "mimeType = 'application/vnd.google-apps.spreadsheet'"
            ")"
        )
        results = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )
        files = results.get("files", [])

        if not files:
            return None, "No CSV, Excel, or Google Sheet files found in the specified Drive folder."

        # Ingest the most recently modified file
        target_file = files[0]
        file_id = target_file["id"]
        file_name = target_file["name"]
        mime_type = target_file.get("mimeType", "")

        file_buffer = io.BytesIO()
        if mime_type == 'application/vnd.google-apps.spreadsheet':
            request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        else:
            request = service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(file_buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        file_buffer.seek(0)

        # Read into pandas based on extension or mime type
        lower_name = file_name.lower()
        if mime_type == 'application/vnd.google-apps.spreadsheet' or lower_name.endswith(".csv"):
            try:
                df = pd.read_csv(file_buffer, encoding='utf-8')
            except UnicodeDecodeError:
                file_buffer.seek(0)
                df = pd.read_csv(file_buffer, encoding='latin1')
        else:
            df = pd.read_excel(file_buffer)

        return df, file_name

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return None, f"⚠️ Google Drive Folder not found (`404`). Please verify the Folder ID and ensure the folder is shared with `examdashboard@examdashboard-508514.iam.gserviceaccount.com` as Viewer."
        elif "403" in error_msg:
            return None, f"⚠️ Access denied (`403`). Please make sure the folder is shared with `examdashboard@examdashboard-508514.iam.gserviceaccount.com` as Viewer."
        return None, f"⚠️ Error accessing Google Drive: {error_msg}"


# --- Application Layout ---
st.title("📊 Executive Operations & Performance Dashboard")

# Folder ID resolution from secrets or interactive UI input
default_folder_id = st.secrets.get("FOLDER_ID", "")
if default_folder_id == "PASTE_YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE":
    default_folder_id = ""

if "user_folder_id" not in st.session_state:
    st.session_state["user_folder_id"] = default_folder_id

folder_id = st.session_state["user_folder_id"]

if not folder_id:
    st.info("👋 Welcome! Please enter your Google Drive Folder ID to connect your data.")
    col_in, col_btn = st.columns([4, 1])
    with col_in:
        input_id = st.text_input(
            "Google Drive Folder ID (from the URL after /folders/):",
            placeholder="e.g. 1a2b3c4d5e6f7g8h9i...",
            key="folder_input"
        )
    with col_btn:
        st.write("")
        st.write("")
        if st.button("Connect Folder", use_container_width=True):
            if input_id.strip():
                st.session_state["user_folder_id"] = input_id.strip()
                st.rerun()

    st.markdown("""
    > [!TIP]
    > **How to get your Folder ID:**
    > 1. Open your folder in [Google Drive](https://drive.google.com/).
    > 2. Look at the browser URL: `https://drive.google.com/drive/folders/1A2b3C4d5E6f7...`
    > 3. Copy the characters after `/folders/` and paste them above (or in `.streamlit/secrets.toml`).
    > 4. Ensure the folder is shared with: `examdashboard@examdashboard-508514.iam.gserviceaccount.com` (Viewer).
    """)
    st.stop()

# Data Retrieval
with st.spinner(f"Fetching latest dataset from Google Drive folder ({folder_id})..."):
    df, meta = load_data_from_drive(folder_id)

if df is None:
    st.error(meta)
    if st.button("Change Folder ID"):
        st.session_state["user_folder_id"] = ""
        st.cache_data.clear()
        st.rerun()
    st.stop()

# Sidebar: Controls & Metadata
with st.sidebar:
    st.subheader("Source Metadata")
    st.caption(f"Active File: `{meta}`")
    if st.button("🔄 Clear Cache & Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Filters")

    # Dynamic categorization filter (detects categorical columns)
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if categorical_cols:
        primary_cat = categorical_cols[0]
        categories = ["All"] + sorted(df[primary_cat].dropna().unique().tolist())
        selected_category = st.selectbox(f"Filter by {primary_cat}", categories)

        if selected_category != "All":
            filtered_df = df[df[primary_cat] == selected_category]
        else:
            filtered_df = df.copy()
    else:
        filtered_df = df.copy()

# Metric Columns (KPIs)
num_cols = filtered_df.select_dtypes(include=["number"]).columns.tolist()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total Records Processed", value=f"{len(filtered_df):,}")

with col2:
    if len(num_cols) >= 1:
        avg_val = filtered_df[num_cols[0]].mean()
        st.metric(label=f"Average {num_cols[0]}", value=f"{avg_val:,.2f}")
    else:
        st.metric(label="Status", value="Optimal")

with col3:
    if len(num_cols) >= 2:
        sum_val = filtered_df[num_cols[1]].sum()
        st.metric(label=f"Total {num_cols[1]}", value=f"{sum_val:,.0f}")
    else:
        completion_rate = (filtered_df.notnull().sum().sum() / filtered_df.size) * 100
        st.metric(label="Data Completeness", value=f"{completion_rate:.1f}%")

with col4:
    unique_entities = filtered_df[categorical_cols[0]].nunique() if categorical_cols else len(filtered_df)
    st.metric(label="Distinct Entities", value=f"{unique_entities:,}")

st.divider()

# Visualizations Row
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Distribution Breakdown")
    if categorical_cols:
        bar_data = (
            filtered_df[categorical_cols[0]]
            .value_counts()
            .head(10)
            .reset_index()
        )
        bar_data.columns = [categorical_cols[0], "Count"]
        fig_bar = px.bar(
            bar_data,
            x=categorical_cols[0],
            y="Count",
            color="Count",
            color_continuous_scale="Blues",
            template="plotly_white",
        )
        fig_bar.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No categorical fields available for distribution charts.")

with chart_col2:
    st.subheader("Correlation & Trends")
    if len(num_cols) >= 2:
        fig_scatter = px.scatter(
            filtered_df,
            x=num_cols[0],
            y=num_cols[1],
            color=categorical_cols[0] if categorical_cols else None,
            template="plotly_white",
            trendline="ols",
        )
        fig_scatter.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_scatter, use_container_width=True)
    elif len(num_cols) == 1:
        fig_hist = px.histogram(
            filtered_df,
            x=num_cols[0],
            nbins=25,
            template="plotly_white",
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("Insufficient numeric data for correlation analytics.")

# Raw Data Exploration
with st.expander("🔍 Inspect Processed Tabular Data", expanded=False):
    st.dataframe(filtered_df, use_container_width=True)
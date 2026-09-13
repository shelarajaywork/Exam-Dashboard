"""
SVKM CED - Academic & Exam Analytics Dashboard
Connects to Google Drive folders and builds dedicated, interactive visual dashboards.
"""
import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px

# Internal modules
import drive_service
import visualizer
import mock_data

# Set Streamlit page layout
st.set_page_config(
    page_title="SVKM CED | Academic Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Metric card styling */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"]:hover {
        border-color: #1e88e5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08);
        transition: all 0.2s ease-in-out;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
    }
    .badge-live {
        background-color: #e8f5e9;
        color: #2e7d32;
    }
    .badge-demo {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1a237e;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #546e7a;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "root_folder_id" not in st.session_state:
    st.session_state["root_folder_id"] = os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")
if "data_cache" not in st.session_state:
    st.session_state["data_cache"] = {}

def get_drive_client():
    """Builds and caches Google Drive client."""
    try:
        return drive_service.build_drive_service()
    except Exception as e:
        st.sidebar.warning(f"Google Drive initialization note: {e}")
        return None

drive_client = get_drive_client()
is_live = (drive_client is not None) and bool(st.session_state["root_folder_id"])

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 🎓 SVKM CED Analytics")
    st.caption("Centralised Examination & Evaluation Dashboard")
    st.markdown("---")

    # Connection Status Indicator
    if is_live:
        st.markdown('<span class="status-badge badge-live">● Live Google Drive Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge badge-demo">● Demo / Sample Mode Active</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Load Folder List
    folders = []
    if is_live:
        try:
            with st.spinner("Fetching folders from Google Drive..."):
                folders = drive_service.list_drive_subfolders(drive_client, st.session_state["root_folder_id"])
        except Exception as e:
            st.error(f"Error listing Drive folders: {e}")
            folders = []

    if not folders:
        # Fallback to mock folders
        folders = mock_data.get_mock_folders()

    folder_names = [f["name"] for f in folders]
    selected_folder_name = st.radio(
        "📂 Select Assessment / Folder:",
        options=folder_names,
        index=0
    )

    selected_folder = next((f for f in folders if f["name"] == selected_folder_name), folders[0])

    st.markdown("---")
    
    # Quick Refresh Action
    if st.button("🔄 Refresh Data Cache", use_container_width=True):
        st.session_state["data_cache"].clear()
        st.rerun()

    # Google Drive Configuration Section
    with st.expander("⚙️ Google Drive Setup", expanded=not is_live):
        st.markdown("#### Connect Your Google Drive")
        st.write("1. Create a Service Account in [Google Cloud Console](https://console.cloud.google.com/).")
        st.write("2. Share your Google Drive root folder with the Service Account email.")
        st.write("3. Provide your Root Folder ID below:")

        input_folder_id = st.text_input(
            "Root Folder ID:",
            value=st.session_state["root_folder_id"],
            help="Extract from Google Drive URL: drive.google.com/drive/folders/YOUR_ID"
        )
        if input_folder_id != st.session_state["root_folder_id"]:
            st.session_state["root_folder_id"] = input_folder_id
            st.session_state["data_cache"].clear()
            st.rerun()

        uploaded_sa = st.file_uploader(
            "Upload service_account.json (Optional):",
            type=["json"],
            help="Upload your Google Cloud service account key file"
        )
        if uploaded_sa is not None:
            try:
                sa_dict = json.load(uploaded_sa)
                with open("service_account.json", "w") as f:
                    json.dump(sa_dict, f, indent=2)
                st.success("Credentials saved to service_account.json!")
                st.rerun()
            except Exception as ex:
                st.error(f"Invalid JSON file: {ex}")

    st.caption("v1.0.0 | Secure Google Drive Integration")

# ----------------- MAIN VIEW -----------------

# Retrieve Data for Selected Folder
folder_id = selected_folder["id"]
cached_data = st.session_state["data_cache"].get(folder_id)

if cached_data is None:
    if is_live and not folder_id.startswith("mock_"):
        with st.spinner(f"Loading data from Drive: {selected_folder_name}..."):
            try:
                df, files = drive_service.load_all_folder_data(drive_client, folder_id)
                st.session_state["data_cache"][folder_id] = (df, files)
                cached_data = (df, files)
            except Exception as e:
                st.error(f"Failed to fetch data from folder: {e}")
                cached_data = (None, [])
    else:
        # Load mock data for demonstration
        df = mock_data.get_mock_folder_data(folder_id)
        files = [{"name": "sample_assessment_data.xlsx", "size": len(df) * 128}]
        cached_data = (df, files)
        st.session_state["data_cache"][folder_id] = cached_data

df_raw, folder_files = cached_data

# Page Title
st.markdown(f'<div class="main-header">{selected_folder["name"]} Dashboard</div>', unsafe_allow_html=True)
if is_live and not folder_id.startswith("mock_"):
    file_list_str = ", ".join([f["name"] for f in folder_files]) if folder_files else "No files"
    st.markdown(f'<div class="sub-header">Live Drive Folder: {selected_folder["name"]} | Source Files: {file_list_str}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="sub-header">Currently viewing sample demonstration data. Connect your Google Cloud credentials to view live files.</div>', unsafe_allow_html=True)

if df_raw is None or df_raw.empty:
    st.info("ℹ️ No data files (CSV, Excel, or Google Sheets) were found in this folder.")
    st.stop()

# Auto-detect column types
col_types = visualizer.detect_column_types(df_raw)

# ----------------- INTERACTIVE FILTERS -----------------
with st.expander("🔍 Filter & Slice Data", expanded=False):
    f_cols = st.columns(min(4, max(1, len(col_types["categorical"]) + 1)))
    filtered_df = df_raw.copy()

    # Categorical filters
    filter_selections = {}
    col_idx = 0
    for cat_col in col_types["categorical"][:3]:  # Top 3 categorical columns
        with f_cols[col_idx % len(f_cols)]:
            unique_vals = sorted([str(x) for x in df_raw[cat_col].dropna().unique()])
            selected = st.multiselect(f"Filter by {cat_col}:", options=unique_vals, default=[])
            filter_selections[cat_col] = selected
            if selected:
                filtered_df = filtered_df[filtered_df[cat_col].astype(str).isin(selected)]
        col_idx += 1

    # Score slider filter
    kpis_preview = visualizer.calculate_kpis(df_raw, col_types)
    score_col = kpis_preview.get("score_col_used")
    if score_col and col_idx < len(f_cols):
        with f_cols[col_idx % len(f_cols)]:
            min_score = float(df_raw[score_col].min())
            max_score = float(df_raw[score_col].max())
            if min_score < max_score:
                score_range = st.slider(
                    f"{score_col} Range:",
                    min_value=min_score,
                    max_value=max_score,
                    value=(min_score, max_score)
                )
                filtered_df = filtered_df[(filtered_df[score_col] >= score_range[0]) & (filtered_df[score_col] <= score_range[1])]

if filtered_df.empty:
    st.warning("⚠️ No records match the active filter criteria. Please broaden your selection.")
    st.stop()

# Compute KPIs for filtered dataset
kpis = visualizer.calculate_kpis(filtered_df, col_types)

# ----------------- TABBED VIEWS -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Executive Overview & KPIs",
    "📊 Deep-Dive Visualizations",
    "🧩 Matrix & Cross-tabulation",
    "📋 Data Explorer & Export"
])

# ----- TAB 1: EXECUTIVE OVERVIEW -----
with tab1:
    st.markdown("### Executive Performance Indicators")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Records", f"{kpis['total_records']:,}")
    with m2:
        if kpis["avg_score"] is not None:
            st.metric(f"Avg {kpis['score_col_used']}", f"{kpis['avg_score']}")
        else:
            st.metric("Avg Score", "N/A")
    with m3:
        if kpis["pass_rate"] is not None:
            st.metric("Pass Rate", f"{kpis['pass_rate']}%")
        else:
            st.metric("Pass Rate", "N/A")
    with m4:
        if kpis["highest_score"] is not None:
            st.metric(f"Highest ({kpis['score_col_used']})", f"{kpis['highest_score']}")
        else:
            st.metric("Highest", "N/A")
    with m5:
        if kpis.get("std_dev") is not None:
            st.metric("Std. Deviation", f"{kpis['std_dev']}")
        else:
            st.metric("Lowest", f"{kpis['lowest_score']}" if kpis["lowest_score"] is not None else "N/A")

    st.markdown("---")

    # High-level overview visuals
    ov_col1, ov_col2 = st.columns(2)
    with ov_col1:
        # Donut of primary categorical column (e.g. Grade or Result Status)
        cat_for_donut = next((c for c in col_types["categorical"] if "grade" in c.lower() or "status" in c.lower() or "result" in c.lower()), None)
        if not cat_for_donut and col_types["categorical"]:
            cat_for_donut = col_types["categorical"][0]

        if cat_for_donut:
            fig_donut = visualizer.plot_grade_distribution(filtered_df, cat_for_donut)
            st.plotly_chart(fig_donut, use_container_width=True)

    with ov_col2:
        # Score Histogram
        if kpis["score_col_used"]:
            fig_hist = visualizer.plot_score_histogram(filtered_df, kpis["score_col_used"])
            st.plotly_chart(fig_hist, use_container_width=True)

# ----- TAB 2: DEEP-DIVE VISUALIZATIONS -----
with tab2:
    st.markdown("### Comparative & Group Analysis")
    
    col_group = None
    for candidate in ["Subject", "Department", "Division", "Course"]:
        for c in col_types["categorical"]:
            if candidate.lower() in c.lower():
                col_group = c
                break
        if col_group:
            break
    if not col_group and col_types["categorical"]:
        col_group = col_types["categorical"][0]

    num_for_chart = kpis["score_col_used"] or (col_types["numeric"][0] if col_types["numeric"] else None)

    v_col1, v_col2 = st.columns(2)
    with v_col1:
        if col_group and num_for_chart:
            fig_bar = visualizer.plot_subject_performance(filtered_df, col_group, num_for_chart)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Insufficient categorical/numeric columns for grouped bar chart.")

    with v_col2:
        # Box plot across division or another categorical group
        alt_group = next((c for c in col_types["categorical"] if c != col_group), col_group)
        if alt_group and num_for_chart:
            fig_box = visualizer.plot_box_distribution(filtered_df, alt_group, num_for_chart)
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("Insufficient columns for distribution box plot.")

    st.markdown("---")

    # Correlation Plot
    st.markdown("### Metric Correlation")
    if len(col_types["numeric"]) >= 2:
        c1, c2 = st.columns([1, 3])
        with c1:
            x_axis = st.selectbox("X-Axis Metric:", options=col_types["numeric"], index=0)
            y_axis_options = [c for c in col_types["numeric"] if c != x_axis] or col_types["numeric"]
            y_axis = st.selectbox("Y-Axis Metric:", options=y_axis_options, index=0)
            color_dim = st.selectbox("Group Color By:", options=["None"] + col_types["categorical"], index=0)
        with c2:
            fig_scatter = visualizer.plot_scatter_correlation(
                filtered_df,
                x_axis,
                y_axis,
                color_col=None if color_dim == "None" else color_dim
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("At least two numerical metrics are needed for correlation scatter plot analysis.")

# ----- TAB 3: MATRIX & TRENDS -----
with tab3:
    st.markdown("### Cross-Tabulation Matrix & Timeline Trends")
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        if len(col_types["categorical"]) >= 2:
            row_c = st.selectbox("Matrix Rows:", options=col_types["categorical"], index=0)
            col_c_options = [c for c in col_types["categorical"] if c != row_c]
            col_c = st.selectbox("Matrix Columns:", options=col_c_options, index=0)
            fig_matrix = visualizer.plot_performance_heatmap(filtered_df, row_c, col_c)
            if fig_matrix:
                st.plotly_chart(fig_matrix, use_container_width=True)
        else:
            st.info("At least two categorical dimensions required for matrix cross-tabulation.")

    with m_col2:
        if col_types["date"] and num_for_chart:
            d_col = col_types["date"][0]
            fig_trend = visualizer.plot_time_trend(filtered_df, d_col, num_for_chart)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No timestamp/date column detected for timeline trend analysis.")

# ----- TAB 4: DATA EXPLORER & EXPORT -----
with tab4:
    st.markdown("### Raw Assessment Dataset")
    st.write(f"Showing **{len(filtered_df)}** records matching active filters.")
    
    # Search box
    search_query = st.text_input("🔎 Search records across all columns:", "")
    display_df = filtered_df
    if search_query:
        mask = display_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
        display_df = display_df[mask]

    st.dataframe(display_df, use_container_width=True, height=450)

    # Download Buttons
    csv_bytes = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv_bytes,
        file_name=f"{selected_folder['name'].replace(' ', '_')}_data.csv",
        mime="text/csv",
        use_container_width=False
    )

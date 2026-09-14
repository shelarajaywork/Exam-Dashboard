"""
modules/evaluation_dashboard.py
Evaluation Dashboard Details page — fully self-contained module.
Displays examiner workload, answer book checking progress, deadline tracking
and stream / course analytics for each college and academic year.
"""
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.drive_utils import (
    SECTION_FOLDER_IDS, list_subfolders, find_files_recursive, download_file
)
from modules.ui_components import (
    MAROON, GOLD, GREEN, AMBER, RED,
    PLOTLY_LAYOUT, page_header, breadcrumb, kpi_card,
    gauge_chart, apply_plotly_theme,
)

TODAY = pd.Timestamp(date.today())


# ── Navigation helpers ──────────────────────────────────────────────────────────

def _build_nav() -> tuple[str, str, str]:
    """
    Renders sidebar navigation for any folder depth:
    Year → Term (optional) → College → Exam Type (optional)
    Returns (year_folder_id, target_folder_id, breadcrumb_label).
    The target_folder_id is the deepest folder the user has selected;
    find_files_recursive will search it and all its children.
    """
    root_id = SECTION_FOLDER_IDS["Evaluation Dashboard Details"]

    # ── Level 1: Academic Year ────────────────────────────────────────
    year_folders = list_subfolders(root_id)
    if not year_folders:
        return root_id, "", ""
    year_names = [f["name"] for f in year_folders]
    default_year_idx = len(year_names) - 1  # last = latest

    st.sidebar.markdown("**Academic Year**")
    chosen_year = st.sidebar.selectbox(
        "Year", year_names, index=default_year_idx, key="eval_year", label_visibility="collapsed"
    )
    year_id = next(f["id"] for f in year_folders if f["name"] == chosen_year)
    label = chosen_year

    # ── Level 2: Term OR College (depends on Drive structure) ──────────
    lvl2_folders = list_subfolders(year_id)
    if not lvl2_folders:
        return year_id, "ALL", label

    lvl2_names = [f["name"] for f in lvl2_folders]
    # Detect whether this level is Terms or Colleges
    is_term_level = any(n.lower().startswith("term") or n.lower().startswith("sem") for n in lvl2_names)
    lvl2_label = "**Term / Semester**" if is_term_level else "**College**"

    st.sidebar.markdown(lvl2_label)
    chosen_lvl2 = st.sidebar.selectbox(
        "Level2", ["All"] + lvl2_names, key="eval_lvl2", label_visibility="collapsed"
    )
    if chosen_lvl2 == "All":
        return year_id, "ALL", label

    lvl2_id = next(f["id"] for f in lvl2_folders if f["name"] == chosen_lvl2)
    label = f"{label} › {chosen_lvl2}"

    # ── Level 3: College (if level 2 was a Term) ───────────────────────
    lvl3_folders = list_subfolders(lvl2_id)
    if not lvl3_folders:
        # lvl2 IS the leaf (college folder directly)
        return year_id, lvl2_id, label

    lvl3_names = [f["name"] for f in lvl3_folders]
    st.sidebar.markdown("**College**")
    chosen_lvl3 = st.sidebar.selectbox(
        "Level3", ["All Colleges"] + lvl3_names, key="eval_lvl3", label_visibility="collapsed"
    )
    if chosen_lvl3 == "All Colleges":
        return year_id, lvl2_id, label

    lvl3_id = next(f["id"] for f in lvl3_folders if f["name"] == chosen_lvl3)
    label = f"{label} › {chosen_lvl3}"

    # ── Level 4: Exam / Batch (Re-exam etc.) ───────────────────────────
    lvl4_folders = list_subfolders(lvl3_id)
    if not lvl4_folders:
        return year_id, lvl3_id, label

    lvl4_names = [f["name"] for f in lvl4_folders]
    st.sidebar.markdown("**Exam / Batch**")
    chosen_lvl4 = st.sidebar.selectbox(
        "Level4", ["All Exams"] + lvl4_names, key="eval_lvl4", label_visibility="collapsed"
    )
    if chosen_lvl4 == "All Exams":
        return year_id, lvl3_id, label

    lvl4_id = next(f["id"] for f in lvl4_folders if f["name"] == chosen_lvl4)
    label = f"{label} › {chosen_lvl4}"
    exam_id = lvl4_id
    return year_id, exam_id, label


# ── Data loading ────────────────────────────────────────────────────────────────

def _load_data(year_id: str, folder_id: str) -> tuple[pd.DataFrame | None, str]:
    """Loads and merges all evaluation sheets under the chosen folder."""
    if folder_id == "ALL":
        # Load all files across all colleges in the selected year
        all_files = find_files_recursive(year_id)
    else:
        all_files = find_files_recursive(folder_id)

    if not all_files:
        return None, ""

    dfs = []
    for f in all_files:
        try:
            df_single = download_file(f["id"], f["name"], f["mimeType"])
            df_single["_source"] = f["name"]
            dfs.append(df_single)
        except Exception as exc:
            st.warning(f"Could not load `{f['name']}`: {exc}")

    if not dfs:
        return None, ""

    df = pd.concat(dfs, ignore_index=True)

    # 1. Exclude completely blank rows & rows where Column A is empty/blank/nan
    first_col = df.columns[0]
    df = df.dropna(how="all")
    df = df[
        df[first_col].notna() &
        (df[first_col].astype(str).str.strip() != "") &
        (df[first_col].astype(str).str.lower() != "nan")
    ]

    # 2. Exclude rows containing "Count:" in Column A (case-insensitive)
    df = df[~df[first_col].astype(str).str.contains(r"\bCount\b|Count:", case=False, na=False)]

    # 3. Exclude CampusName and StreamName columns
    cols_to_drop = [c for c in ["CampusName", "StreamName"] if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Numeric coercion
    for c in ["PresentCount", "CheckCount", "UnCheckCount", "InprogressCount", "RejectCount", "UploadCount"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # String sanitization to prevent PyArrow mixed-type errors
    if "Mobile" in df.columns:
        df["Mobile"] = df["Mobile"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)

    # Date parsing
    for dc in ["EvaluationLastDate", "ExamDate", "AssignedDateTime"]:
        if dc in df.columns:
            df[dc + "_dt"] = pd.to_datetime(df[dc], format="%d/%m/%Y", errors="coerce")

    # Deadline flag
    if "EvaluationLastDate_dt" in df.columns:
        df["_deadline_days"] = (df["EvaluationLastDate_dt"] - TODAY).dt.days
        df["_deadline_status"] = df["_deadline_days"].apply(
            lambda d: "Overdue" if d < 0 else ("Due Today" if d == 0 else "Upcoming")
        )

    file_names = ", ".join(f["name"][:40] for f in all_files[:3])
    return df, file_names


# ── KPI row ─────────────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame):
    total_present = int(df["PresentCount"].sum())
    total_checked = int(df["CheckCount"].sum())
    total_uncheck = int(df["UnCheckCount"].sum())
    total_inprog  = int(df.get("InprogressCount", pd.Series(0)).sum())
    eval_rate     = (total_checked / total_present * 100) if total_present > 0 else 0
    examiners     = df["ExaminerName"].nunique() if "ExaminerName" in df.columns else 0
    overdue_count = int((df["_deadline_days"] < 0).sum()) if "_deadline_days" in df.columns else 0

    cols = st.columns(6)
    with cols[0]:
        kpi_card("Total Answer Books", f"{total_present:,}", accent="maroon")
    with cols[1]:
        kpi_card("Evaluated", f"{total_checked:,}",
                 delta=f"{eval_rate:.1f}% complete", delta_dir="up", accent="green")
    with cols[2]:
        kpi_card("Pending", f"{total_uncheck:,}",
                 delta="Awaiting evaluation", delta_dir="down" if total_uncheck > 0 else "neutral",
                 accent="red")
    with cols[3]:
        kpi_card("In Progress", f"{total_inprog:,}", accent="gold")
    with cols[4]:
        kpi_card("Active Examiners", f"{examiners:,}", accent="blue")
    with cols[5]:
        kpi_card("Overdue Deadlines", f"{overdue_count:,}",
                 delta="Examiners past due date", delta_dir="down" if overdue_count > 0 else "up",
                 accent="red" if overdue_count > 0 else "green")


# ── Tab 1: Overview ─────────────────────────────────────────────────────────────

def _tab_overview(df: pd.DataFrame):
    total_present = float(df["PresentCount"].sum())
    total_checked = float(df["CheckCount"].sum())
    total_uncheck = float(df["UnCheckCount"].sum())
    total_inprog  = float(df.get("InprogressCount", pd.Series(0)).sum())
    total_reject  = float(df.get("RejectCount",    pd.Series(0)).sum())
    eval_rate     = (total_checked / total_present * 100) if total_present > 0 else 0

    g_col, d_col, s_col = st.columns([1, 1.5, 1.5])

    # Gauge
    with g_col:
        st.plotly_chart(gauge_chart(round(eval_rate, 1), "Overall Completion"), use_container_width=True)

    # Donut status breakdown
    with d_col:
        status_data = pd.DataFrame({
            "Status": ["Checked ✔", "Pending ✗", "In Progress ⏳", "Rejected"],
            "Count": [total_checked, total_uncheck, total_inprog, total_reject],
        }).query("Count > 0")

        colour_map = {
            "Checked ✔": GREEN, "Pending ✗": RED,
            "In Progress ⏳": AMBER, "Rejected": "#9E9E9E",
        }
        fig_donut = px.pie(
            status_data, names="Status", values="Count", hole=0.50,
            title="Answer Book Status Breakdown",
            color="Status", color_discrete_map=colour_map,
        )
        fig_donut.update_traces(
            textposition="inside", textinfo="percent+label",
            marker=dict(line=dict(color="white", width=2))
        )
        apply_plotly_theme(fig_donut, height=320)
        st.plotly_chart(fig_donut, use_container_width=True)

    # Role progress bars
    with s_col:
        group_col = "RoleName" if "RoleName" in df.columns else ("Semester/Trimester" if "Semester/Trimester" in df.columns else None)
        if group_col:
            role_df = df.groupby(group_col).agg(
                Present=("PresentCount", "sum"),
                Checked=("CheckCount",   "sum"),
            ).reset_index()
            role_df["Pct"] = (role_df["Checked"] / role_df["Present"] * 100).round(1).fillna(0)
            role_df = role_df.sort_values("Present", ascending=True)

            fig_s = px.bar(
                role_df, x="Present", y=group_col, orientation="h",
                title=f"Papers by {group_col} (Completion %)",
                color="Pct", color_continuous_scale=[[0, RED], [0.5, AMBER], [1, GREEN]],
                text=role_df["Pct"].apply(lambda v: f"{v:.0f}%"),
            )
            fig_s.update_traces(textposition="outside")
            apply_plotly_theme(fig_s, height=320)
            st.plotly_chart(fig_s, use_container_width=True)


# ── Tab 2: Deep-Dive ─────────────────────────────────────────────────────────────

def _tab_deepdive(df: pd.DataFrame):
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Course-Level Evaluation Status")
        if "CourseName" in df.columns:
            c_df = df.groupby("CourseName").agg(
                Checked=("CheckCount", "sum"),
                Pending=("UnCheckCount", "sum"),
            ).reset_index().sort_values("Checked", ascending=False).head(12)
            c_df.columns = ["Course", "Checked ✔", "Pending ✗"]

            fig_c = px.bar(
                c_df.melt(id_vars="Course", var_name="Status", value_name="Count"),
                x="Count", y="Course", color="Status", orientation="h",
                barmode="stack", title="Course-wise Status (Top 12 by Volume)",
                color_discrete_map={"Checked ✔": GREEN, "Pending ✗": RED},
            )
            apply_plotly_theme(fig_c, height=420)
            st.plotly_chart(fig_c, use_container_width=True)

    with col_b:
        st.subheader("Top Examiner Productivity")
        if "ExaminerName" in df.columns:
            ex_df = df.groupby("ExaminerName").agg(
                Present=("PresentCount", "sum"),
                Checked=("CheckCount",   "sum"),
                Pending=("UnCheckCount", "sum"),
            ).reset_index()
            ex_df["Pct"] = (ex_df["Checked"] / ex_df["Present"] * 100).round(1).fillna(0)
            ex_df = ex_df.sort_values("Checked", ascending=False).head(12)

            fig_ex = px.bar(
                ex_df, x="Checked", y="ExaminerName", orientation="h",
                title="Top 12 Examiners — Papers Checked",
                color="Pct", color_continuous_scale=[[0, RED], [0.5, AMBER], [1, GREEN]],
                text=ex_df["Checked"].apply(lambda v: f"{int(v):,}"),
                labels={"Pct": "Completion %"},
            )
            fig_ex.update_traces(textposition="outside")
            apply_plotly_theme(fig_ex, height=420)
            st.plotly_chart(fig_ex, use_container_width=True)


# ── Tab 3: Deadline Tracker ───────────────────────────────────────────────────────

def _tab_deadlines(df: pd.DataFrame):
    st.subheader("Evaluation Deadline Tracker")

    if "_deadline_days" not in df.columns:
        st.info("No EvaluationLastDate column found in this dataset.")
        return

    needed_cols = ["ExaminerName", "RoleName", "CourseName", "EvaluationLastDate",
                   "_deadline_days", "_deadline_status", "UnCheckCount", "CheckCount"]
    avail = [c for c in needed_cols if c in df.columns]
    tracker = df[avail].copy().drop_duplicates()
    tracker = tracker.rename(columns={
        "EvaluationLastDate": "Deadline",
        "_deadline_days":     "Days Until Deadline",
        "_deadline_status":   "Status",
    })
    tracker = tracker.sort_values("Days Until Deadline")

    # Summary metrics
    overdue_n  = int((tracker["Days Until Deadline"] < 0).sum())
    today_n    = int((tracker["Days Until Deadline"] == 0).sum())
    upcoming_n = int((tracker["Days Until Deadline"] > 0).sum())

    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("🔴 Overdue Deadlines", f"{overdue_n:,}")
    with b2:
        st.metric("🟡 Due Today", f"{today_n:,}")
    with b3:
        st.metric("🟢 Upcoming Deadlines", f"{upcoming_n:,}")

    # Display clean table without hardcoded row backgrounds
    tracker_disp = tracker.copy()
    tracker_disp["Status"] = tracker_disp["Status"].apply(
        lambda s: "🔴 Overdue" if s == "Overdue" else ("🟡 Due Today" if s == "Due Today" else "🟢 Upcoming")
    )

    st.dataframe(tracker_disp, use_container_width=True, height=420)

    # Deadline timeline chart
    if "Deadline" in tracker.columns and not tracker.empty:
        deadline_summary = tracker.groupby("Deadline")["Days Until Deadline"].first().reset_index()
        deadline_summary["Status"] = deadline_summary["Days Until Deadline"].apply(
            lambda d: "Overdue" if d < 0 else ("Due Today" if d == 0 else "Upcoming")
        )
        fig_tl = px.scatter(
            deadline_summary, x="Deadline", y=[0] * len(deadline_summary),
            color="Status",
            color_discrete_map={"Overdue": RED, "Due Today": AMBER, "Upcoming": GREEN},
            title="Evaluation Deadline Timeline",
            size=[15] * len(deadline_summary),
        )
        fig_tl.update_yaxes(visible=False)
        apply_plotly_theme(fig_tl, height=180)
        st.plotly_chart(fig_tl, use_container_width=True)


# ── Tab 4: Records ───────────────────────────────────────────────────────────────

def _tab_records(df: pd.DataFrame, folder_label: str):
    st.subheader("Evaluation Records Explorer")

    search = st.text_input("Search by examiner name, course, role, category or status:", "")
    disp = df.copy()
    if search:
        mask = disp.astype(str).apply(lambda row: row.str.contains(search, case=False).any(), axis=1)
        disp = disp[mask]

    # Drop internal helper columns
    disp_clean = disp[[c for c in disp.columns if not c.startswith("_")]]
    st.caption(f"Showing **{len(disp_clean):,}** records")
    st.dataframe(disp_clean, use_container_width=True, height=440)

    csv = disp_clean.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Export to CSV", csv,
        file_name=f"Evaluation_{folder_label.replace(' ', '_')}.csv",
        mime="text/csv",
    )


# ── Main entry point ─────────────────────────────────────────────────────────────

def render():
    """Called from app.py to render the full Evaluation Dashboard Details page."""

    page_header(
        "Evaluation Dashboard Details",
        "Live tracking of answer book evaluations, examiner workload and deadline compliance",
        icon="📋"
    )

    # Sidebar navigation
    st.sidebar.markdown("---")
    year_id, folder_id, folder_label = _build_nav()

    if not folder_id:
        st.info("No sub-folders found inside this academic year. Please add college folders in Google Drive.")
        return

    # Load data
    with st.spinner("Fetching evaluation data from Google Drive…"):
        df, file_names = _load_data(year_id if folder_id == "ALL" else folder_id, folder_id)

    if df is None or df.empty:
        st.warning(f"No evaluation sheets found under **{folder_label}**.")
        if "2024-25" in folder_label:
            st.info("💡 **Tip**: Live evaluation sheets are currently located in **2025-26 › Term II** (N. M. College & UPG College). Select **2025-26** above to view the dashboard.")
        return

    # Breadcrumb
    breadcrumb("Evaluation Dashboard Details", folder_label)

    # ── Filters ───────────────────────────────────────────────────────
    with st.expander("🔍 Filter Evaluation Records", expanded=False):
        filtered = df.copy()

        # Row 1: ExaminerName, RoleName, CourseName
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        if "ExaminerName" in df.columns:
            with r1_col1:
                examiner_options = sorted([str(x) for x in df["ExaminerName"].dropna().unique()])
                sel_examiner = st.multiselect("Examiner Name", examiner_options, key="ef_examiner")
                if sel_examiner:
                    filtered = filtered[filtered["ExaminerName"].isin(sel_examiner)]

        if "RoleName" in df.columns:
            with r1_col2:
                role_options = sorted([str(x) for x in df["RoleName"].dropna().unique()])
                sel_role = st.multiselect("Role Name", role_options, key="ef_role")
                if sel_role:
                    filtered = filtered[filtered["RoleName"].isin(sel_role)]

        if "CourseName" in df.columns:
            with r1_col3:
                course_options = sorted([str(x) for x in df["CourseName"].dropna().unique()])
                sel_course = st.multiselect("Course Name", course_options, key="ef_course")
                if sel_course:
                    filtered = filtered[filtered["CourseName"].isin(sel_course)]

        # Row 2: Semester/Trimester, CategoryName, Exam Start Date, Exam End Date
        r2_col1, r2_col2, r2_col3, r2_col4 = st.columns([1.2, 1.8, 1, 1])

        if "Semester/Trimester" in df.columns:
            with r2_col1:
                sem_options = sorted([str(x) for x in df["Semester/Trimester"].dropna().unique()])
                sel_sem = st.multiselect("Semester / Trimester", sem_options, key="ef_sem")
                if sel_sem:
                    filtered = filtered[filtered["Semester/Trimester"].isin(sel_sem)]

        if "CategoryName" in df.columns:
            with r2_col2:
                cat_options = sorted([str(x) for x in df["CategoryName"].dropna().unique()])
                sel_cat = st.multiselect("Category Name", cat_options, key="ef_cat")
                if sel_cat:
                    filtered = filtered[filtered["CategoryName"].isin(sel_cat)]

        # Calendar dropdown filters for ExamDate
        if "ExamDate_dt" in df.columns and df["ExamDate_dt"].notna().any():
            valid_dates = df["ExamDate_dt"].dropna()
            min_exam_d = valid_dates.min().date()
            max_exam_d = valid_dates.max().date()

            with r2_col3:
                start_date = st.date_input(
                    "Exam Start Date",
                    value=min_exam_d,
                    min_value=min_exam_d,
                    max_value=max_exam_d,
                    format="DD/MM/YYYY",
                    key="ef_start_date"
                )

            with r2_col4:
                end_date = st.date_input(
                    "Exam End Date",
                    value=max_exam_d,
                    min_value=min_exam_d,
                    max_value=max_exam_d,
                    format="DD/MM/YYYY",
                    key="ef_end_date"
                )

            if start_date and end_date:
                if start_date > end_date:
                    st.warning("⚠️ 'Exam Start Date' cannot be later than 'Exam End Date'.")
                else:
                    filtered = filtered[
                        (filtered["ExamDate_dt"].dt.date >= start_date) &
                        (filtered["ExamDate_dt"].dt.date <= end_date)
                    ]

    # ── KPI Strip ─────────────────────────────────────────────────────
    st.markdown("&nbsp;", unsafe_allow_html=True)
    _render_kpis(filtered)
    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview & Progress",
        "🔎 Deep-Dive Analytics",
        "📅 Deadline Tracker",
        "📋 Records & Export",
    ])

    with tab1: _tab_overview(filtered)
    with tab2: _tab_deepdive(filtered)
    with tab3: _tab_deadlines(filtered)
    with tab4: _tab_records(filtered, folder_label)

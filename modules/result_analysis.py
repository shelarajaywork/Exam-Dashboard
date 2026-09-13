"""
modules/result_analysis.py
Result Analysis page — fully self-contained module.
Analyses Grade Master Reports (GMR): student grades, SGPA distribution,
module-wise performance, and gender analytics.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.drive_utils import (
    SECTION_FOLDER_IDS, list_subfolders, find_files_recursive, download_file
)
from modules.ui_components import (
    MAROON, GOLD, GREEN, AMBER, RED, BLUE, PLOTLY_LAYOUT,
    page_header, breadcrumb, kpi_card, apply_plotly_theme,
)


# ── Navigation helpers ──────────────────────────────────────────────────────────

def _build_nav() -> tuple[str, str, str]:
    """
    Dynamic nav: Year → Term (optional) → College → Sub-folder (optional).
    Returns (root_search_folder_id, target_folder_id, label).
    """
    root_id = SECTION_FOLDER_IDS["Result Analysis"]

    # ── Level 1: Academic Year ─────────────────────────────────────────
    year_folders = list_subfolders(root_id)
    if not year_folders:
        return root_id, "ALL", "All"
    year_names  = [f["name"] for f in year_folders]
    default_idx = len(year_names) - 1

    st.sidebar.markdown("**Academic Year**")
    chosen_year = st.sidebar.selectbox(
        "Year", year_names, index=default_idx, key="ra_year", label_visibility="collapsed"
    )
    year_id = next(f["id"] for f in year_folders if f["name"] == chosen_year)
    label = chosen_year

    # ── Level 2: Term OR College ───────────────────────────────────────
    lvl2_folders = list_subfolders(year_id)
    if not lvl2_folders:
        return year_id, "ALL", label

    lvl2_names = [f["name"] for f in lvl2_folders]
    is_term_level = any(n.lower().startswith("term") or n.lower().startswith("sem") for n in lvl2_names)
    lvl2_label = "**Term / Semester**" if is_term_level else "**College**"

    st.sidebar.markdown(lvl2_label)
    chosen_lvl2 = st.sidebar.selectbox(
        "Level2", ["All"] + lvl2_names, key="ra_lvl2", label_visibility="collapsed"
    )
    if chosen_lvl2 == "All":
        return year_id, "ALL", label

    lvl2_id = next(f["id"] for f in lvl2_folders if f["name"] == chosen_lvl2)
    label = f"{label} › {chosen_lvl2}"

    # ── Level 3: College (if level 2 was Term) ─────────────────────────
    lvl3_folders = list_subfolders(lvl2_id)
    if not lvl3_folders:
        return lvl2_id, "ALL", label

    lvl3_names = [f["name"] for f in lvl3_folders]
    st.sidebar.markdown("**College**")
    chosen_lvl3 = st.sidebar.selectbox(
        "Level3", ["All Colleges"] + lvl3_names, key="ra_lvl3", label_visibility="collapsed"
    )
    if chosen_lvl3 == "All Colleges":
        return lvl2_id, "ALL", label

    lvl3_id = next(f["id"] for f in lvl3_folders if f["name"] == chosen_lvl3)
    label = f"{label} › {chosen_lvl3}"

    # ── Level 4: Sub-folder (GMR Files, Re-exam, etc.) ─────────────────
    lvl4_folders = list_subfolders(lvl3_id)
    if not lvl4_folders:
        return lvl3_id, "ALL", label

    lvl4_names = [f["name"] for f in lvl4_folders]
    st.sidebar.markdown("**Sub-folder / Exam Type**")
    chosen_lvl4 = st.sidebar.selectbox(
        "Level4", ["All Files"] + lvl4_names, key="ra_lvl4", label_visibility="collapsed"
    )
    if chosen_lvl4 == "All Files":
        return lvl3_id, "ALL", label

    lvl4_id = next(f["id"] for f in lvl4_folders if f["name"] == chosen_lvl4)
    return lvl4_id, "ALL", f"{label} › {chosen_lvl4}"



# ── Data loading ────────────────────────────────────────────────────────────────

def _load_data(folder_id: str) -> tuple[pd.DataFrame | None, list[dict]]:
    all_files = find_files_recursive(folder_id)
    if not all_files:
        return None, []

    dfs = []
    for f in all_files:
        try:
            df_single = download_file(f["id"], f["name"], f["mimeType"])
            df_single["_source_file"] = f["name"]
            dfs.append(df_single)
        except Exception as exc:
            st.warning(f"Could not load `{f['name']}`: {exc}")

    if not dfs:
        return None, all_files

    df = pd.concat(dfs, ignore_index=True)

    # Numeric coercion for common columns
    for col in ["Total", "Aggregate", "Percentage", "SGPA", "CGPA",
                "MAX Marks", "Attempted Credit Value", "Graded Credit Value"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Detect key columns
    df.attrs["student_id_col"] = next(
        (c for c in ["Student Number", "ID number", "Roll No", "PRN", "Student_ID"] if c in df.columns), None
    )
    df.attrs["student_name_col"] = next(
        (c for c in ["Student Name", "Name", "StudentName"] if c in df.columns), None
    )
    df.attrs["module_col"] = next(
        (c for c in ["Module", "Course", "Subject", "CourseName"] if c in df.columns), None
    )
    df.attrs["grade_col"] = next(
        (c for c in ["Grades", "Grade", "Grade symbol"] if c in df.columns), None
    )
    df.attrs["result_col"] = next(
        (c for c in ["Result", "Status", "Result_Status"] if c in df.columns), None
    )

    return df, all_files


# ── File selector (inside the page) ────────────────────────────────────────────

def _file_selector(all_files: list[dict]) -> pd.DataFrame | None:
    if not all_files:
        return None
    file_names = [f["name"] for f in all_files]
    if len(all_files) == 1:
        st.caption(f"Source: **{file_names[0]}**")
        return None  # already loaded
    options = ["📊 Consolidated (All Files)"] + file_names
    sel = st.selectbox("Select GMR / Exam File:", options, key="ra_file")
    return sel


# ── SGPA banding helper ─────────────────────────────────────────────────────────

def _sgpa_band(sgpa_series: pd.Series) -> pd.DataFrame:
    bins   = [0, 5, 6, 7, 8, 9, 10.01]
    labels = ["Below 5 (At Risk)", "5–6 (Satisfactory)", "6–7 (Average)",
              "7–8 (Good)", "8–9 (Excellent)", "9–10 (Outstanding)"]
    banded = pd.cut(sgpa_series.dropna(), bins=bins, labels=labels, right=False)
    return banded.value_counts().reindex(labels, fill_value=0).reset_index()


# ── KPI row ─────────────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame):
    sid_col = df.attrs.get("student_id_col")
    sname_col = df.attrs.get("student_name_col")
    grade_col = df.attrs.get("grade_col")
    result_col = df.attrs.get("result_col")

    total_recs  = len(df)
    uniq_stud   = df[sid_col].nunique() if sid_col else (df[sname_col].nunique() if sname_col else total_recs)
    avg_sgpa    = df["SGPA"].dropna().mean() if "SGPA" in df.columns else None
    max_sgpa    = df["SGPA"].dropna().max()  if "SGPA" in df.columns else None

    pass_rate = None
    if result_col and result_col in df.columns:
        pass_n   = df[result_col].astype(str).str.lower().str.contains("pass").sum()
        pass_rate = round(pass_n / len(df) * 100, 1)
    elif "SGPA" in df.columns:
        pass_rate = round((df["SGPA"] >= 5.0).sum() / len(df) * 100, 1)

    cols = st.columns(5)
    with cols[0]:
        kpi_card("Total Records", f"{total_recs:,}", accent="maroon")
    with cols[1]:
        kpi_card("Unique Students", f"{uniq_stud:,}", accent="gold")
    with cols[2]:
        kpi_card("Average SGPA", f"{avg_sgpa:.2f}" if avg_sgpa else "N/A",
                 delta=f"Highest: {max_sgpa:.2f}" if max_sgpa else "",
                 delta_dir="up", accent="blue")
    with cols[3]:
        kpi_card("Pass Rate", f"{pass_rate}%" if pass_rate else "N/A",
                 delta_dir="up" if pass_rate and pass_rate >= 70 else "down",
                 accent="green" if pass_rate and pass_rate >= 70 else "red")
    with cols[4]:
        mod_col = df.attrs.get("module_col")
        mod_count = df[mod_col].nunique() if mod_col else 0
        kpi_card("Total Modules", f"{mod_count}", accent="maroon")


# ── Tab 1: Grade Overview ─────────────────────────────────────────────────────────

def _tab_overview(df: pd.DataFrame):
    grade_col = df.attrs.get("grade_col")
    g1, g2 = st.columns(2)

    with g1:
        if grade_col and grade_col in df.columns:
            grade_counts = (
                df[grade_col].astype(str).value_counts().head(12).reset_index()
            )
            grade_counts.columns = ["Grade", "Count"]
            fig_g = px.pie(
                grade_counts, names="Grade", values="Count", hole=0.45,
                title="Grade Distribution Breakdown",
                color_discrete_sequence=[
                    MAROON, GOLD, "#3A6186", GREEN, AMBER, "#8E24AA", RED, "#00796B",
                    "#5D4037", "#1565C0", "#F57C00", "#C62828",
                ],
            )
            fig_g.update_traces(
                textposition="inside", textinfo="percent+label",
                marker=dict(line=dict(color="white", width=2))
            )
            apply_plotly_theme(fig_g, height=340)
            st.plotly_chart(fig_g, use_container_width=True)
        else:
            st.info("No grade column detected.")

    with g2:
        if "SGPA" in df.columns and not df["SGPA"].dropna().empty:
            band_df = _sgpa_band(df["SGPA"])
            band_df.columns = ["SGPA Band", "Student Count"]
            colours = [RED, AMBER, "#FDD835", GREEN, "#1B5E20", MAROON]
            fig_band = px.bar(
                band_df, x="SGPA Band", y="Student Count",
                title="SGPA Band Distribution",
                color="SGPA Band",
                color_discrete_sequence=colours,
                text="Student Count",
            )
            fig_band.update_traces(textposition="outside", showlegend=False)
            apply_plotly_theme(fig_band, height=340)
            st.plotly_chart(fig_band, use_container_width=True)
        elif "Percentage" in df.columns and not df["Percentage"].dropna().empty:
            pct = df["Percentage"].dropna()
            fig_hist = px.histogram(
                df.dropna(subset=["Percentage"]), x="Percentage", nbins=25,
                title="Percentage Distribution",
                color_discrete_sequence=[MAROON], marginal="box",
            )
            apply_plotly_theme(fig_hist, height=340)
            st.plotly_chart(fig_hist, use_container_width=True)


# ── Tab 2: Module Performance ─────────────────────────────────────────────────────

def _tab_modules(df: pd.DataFrame):
    mod_col = df.attrs.get("module_col")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Module-wise Average Marks")
        if mod_col and "Total" in df.columns:
            mod_df = (
                df.groupby(mod_col)["Total"]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"mean": "Avg Marks", "count": "Entries"})
            )
            mod_df["Avg Marks"] = mod_df["Avg Marks"].round(1)
            mod_df = mod_df.sort_values("Avg Marks", ascending=True).tail(12)
            fig_mod = px.bar(
                mod_df, x="Avg Marks", y=mod_col, orientation="h",
                title="Average Marks by Module (Top 12)",
                color="Avg Marks",
                color_continuous_scale=[[0, RED], [0.5, GOLD], [1, GREEN]],
                text="Avg Marks",
            )
            fig_mod.update_traces(textposition="outside")
            apply_plotly_theme(fig_mod, height=420)
            st.plotly_chart(fig_mod, use_container_width=True)
        else:
            st.info("Module and Total columns required for this chart.")

    with col_b:
        st.subheader("SGPA Distribution (Violin)")
        if mod_col and "SGPA" in df.columns and not df["SGPA"].dropna().empty:
            top_mods = df[mod_col].value_counts().head(6).index.tolist()
            sub = df[df[mod_col].isin(top_mods)].dropna(subset=["SGPA"])
            if not sub.empty:
                fig_vio = px.violin(
                    sub, x=mod_col, y="SGPA", color=mod_col,
                    box=True, points="outliers",
                    title="SGPA spread by Module (Top 6)",
                    color_discrete_sequence=[MAROON, GOLD, "#3A6186", GREEN, AMBER, "#8E24AA"],
                )
                fig_vio.update_layout(showlegend=False)
                apply_plotly_theme(fig_vio, height=420)
                st.plotly_chart(fig_vio, use_container_width=True)
            else:
                st.info("Insufficient data for violin chart.")
        else:
            st.info("SGPA and Module columns required.")


# ── Tab 3: Comparisons ─────────────────────────────────────────────────────────────

def _tab_comparisons(df: pd.DataFrame):
    col_a, col_b = st.columns(2)
    mod_col = df.attrs.get("module_col")

    with col_a:
        st.subheader("Gender Performance Comparison")
        metric = "SGPA" if "SGPA" in df.columns else ("Total" if "Total" in df.columns else None)
        if "Gender" in df.columns and metric:
            gen_df = df.dropna(subset=[metric, "Gender"])
            fig_gen = px.box(
                gen_df, x="Gender", y=metric, color="Gender",
                points="outliers",
                title=f"{metric} by Gender",
                color_discrete_map={
                    "Male": BLUE, "Female": MAROON,
                    "M": BLUE, "F": MAROON,
                },
            )
            fig_gen.update_layout(showlegend=False)
            apply_plotly_theme(fig_gen, height=360)
            st.plotly_chart(fig_gen, use_container_width=True)
        else:
            st.info("Gender and SGPA/Total columns required.")

    with col_b:
        st.subheader("Pass vs Fail by Module")
        result_col = df.attrs.get("result_col")
        if mod_col and result_col and result_col in df.columns:
            top_mods = df[mod_col].value_counts().head(8).index.tolist()
            sub = df[df[mod_col].isin(top_mods)]
            sub = sub.copy()
            sub["Result_Clean"] = sub[result_col].astype(str).str.lower().fillna("").map(
                lambda r: "Pass" if "pass" in r else ("Fail" if "fail" in r else "Other")
            )
            pf = sub.groupby([mod_col, "Result_Clean"]).size().reset_index(name="Count")
            fig_pf = px.bar(
                pf, x="Count", y=mod_col, color="Result_Clean",
                orientation="h", barmode="stack",
                title="Pass / Fail per Module (Top 8)",
                color_discrete_map={"Pass": GREEN, "Fail": RED, "Other": GOLD},
            )
            apply_plotly_theme(fig_pf, height=360)
            st.plotly_chart(fig_pf, use_container_width=True)
        else:
            st.info("Module and Result columns required.")


# ── Tab 4: GMR Records ─────────────────────────────────────────────────────────────

def _tab_records(df: pd.DataFrame, label: str):
    st.subheader("Grade Master Report (GMR)")
    search = st.text_input("Search by student name, module, grade or program:", "")
    disp = df.copy()
    if search:
        mask = disp.astype(str).apply(lambda row: row.str.contains(search, case=False).any(), axis=1)
        disp = disp[mask]
    disp_clean = disp[[c for c in disp.columns if not c.startswith("_")]]
    st.caption(f"Showing **{len(disp_clean):,}** records")
    st.dataframe(disp_clean, use_container_width=True, height=440)

    csv = disp_clean.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Export to CSV", csv,
        file_name=f"ResultAnalysis_{label.replace(' ', '_')}.csv",
        mime="text/csv",
    )


# ── Main entry point ─────────────────────────────────────────────────────────────

def render():
    """Called from app.py to render the Result Analysis page."""

    page_header(
        "Result Analysis",
        "Student grade analytics, SGPA performance, module comparisons and GMR deep-dive",
        icon="📊",
    )

    st.sidebar.markdown("---")
    folder_id, _, label = _build_nav()

    with st.spinner("Fetching result data from Google Drive…"):
        df, all_files = _load_data(folder_id)

    if df is None or df.empty:
        st.warning(f"No examination result files found under **{label}**.")
        if "2025-26" in label:
            st.info("💡 **Tip**: Examination data is available in **2024-25 › Term I › N. M. College › GMR Files**. Select **2024-25** in the sidebar above to view the analysis, or upload new files to this folder in Google Drive.")
        return

    breadcrumb("Result Analysis", label)

    # ── Filters ───────────────────────────────────────────────────────
    mod_col    = df.attrs.get("module_col")
    grade_col  = df.attrs.get("grade_col")
    result_col = df.attrs.get("result_col")

    with st.expander("🔍 Filter Data", expanded=False):
        fc = st.columns(3)
        filtered = df.copy()
        # Preserve attrs
        filtered.attrs = df.attrs

        if mod_col and mod_col in df.columns:
            with fc[0]:
                sel = st.multiselect("Module / Subject", sorted(df[mod_col].dropna().unique()), key="ra_fmod")
                if sel:
                    filtered = filtered[filtered[mod_col].isin(sel)]
                    filtered.attrs = df.attrs
        if grade_col and grade_col in df.columns:
            with fc[1]:
                sel = st.multiselect("Grade", sorted(df[grade_col].dropna().astype(str).unique()), key="ra_fgrade")
                if sel:
                    filtered = filtered[filtered[grade_col].astype(str).isin(sel)]
                    filtered.attrs = df.attrs
        if "Gender" in df.columns:
            with fc[2]:
                sel = st.multiselect("Gender", sorted(df["Gender"].dropna().unique()), key="ra_fgender")
                if sel:
                    filtered = filtered[filtered["Gender"].isin(sel)]
                    filtered.attrs = df.attrs

    # ── KPI Strip ─────────────────────────────────────────────────────
    st.markdown("&nbsp;", unsafe_allow_html=True)
    _render_kpis(filtered)
    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Grade & SGPA Overview",
        "📚 Module Performance",
        "⚖️ Comparisons",
        "📋 GMR Records & Export",
    ])

    with tab1: _tab_overview(filtered)
    with tab2: _tab_modules(filtered)
    with tab3: _tab_comparisons(filtered)
    with tab4: _tab_records(filtered, label)

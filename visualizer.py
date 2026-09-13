"""
Visualizer Engine.
Generates interactive, publication-quality Plotly visuals and KPI cards
tailored for exam results, evaluations, and general tabular datasets.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple

# Modern color palette
THEME_COLORS = px.colors.qualitative.Prism
ACCENT_BLUE = "#1E88E5"
ACCENT_GREEN = "#43A047"
ACCENT_RED = "#E53935"
ACCENT_PURPLE = "#8E24AA"
BG_CARD = "#F8F9FA"

def detect_column_types(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Intelligently categorizes dataframe columns into numeric, categorical, date, and identifier columns.
    """
    numeric_cols = []
    categorical_cols = []
    date_cols = []
    id_cols = []

    for col in df.columns:
        if col.startswith('_source'):
            continue
        # Check date
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
            continue
        try:
            # Try parsing strings as date if column name has date/time keywords
            if any(k in col.lower() for k in ["date", "time", "day"]):
                pd.to_datetime(df[col], errors='raise')
                date_cols.append(col)
                continue
        except Exception:
            pass

        # Check numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            # If low cardinality integer like binary 0/1 or ID
            if "id" in col.lower() or "roll" in col.lower() or "prn" in col.lower():
                id_cols.append(col)
            else:
                numeric_cols.append(col)
        else:
            # Non-numeric
            if "id" in col.lower() or "roll" in col.lower() or "prn" in col.lower() or "name" in col.lower():
                id_cols.append(col)
            else:
                categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "date": date_cols,
        "id": id_cols
    }

def calculate_kpis(df: pd.DataFrame, col_types: Dict[str, List[str]]) -> Dict[str, Any]:
    """Calculates executive summary KPIs from the data."""
    kpis = {
        "total_records": len(df),
        "avg_score": None,
        "pass_rate": None,
        "highest_score": None,
        "lowest_score": None,
        "score_col_used": None
    }

    # Find the primary score column
    score_col = None
    for candidate in ["Marks_Obtained", "Percentage", "Score", "Total", "Marks", "Percent"]:
        for col in col_types["numeric"]:
            if candidate.lower() in col.lower():
                score_col = col
                break
        if score_col:
            break

    if not score_col and col_types["numeric"]:
        score_col = col_types["numeric"][0]

    if score_col:
        kpis["score_col_used"] = score_col
        series = df[score_col].dropna()
        if not series.empty:
            kpis["avg_score"] = round(float(series.mean()), 1)
            kpis["highest_score"] = float(series.max())
            kpis["lowest_score"] = float(series.min())
            kpis["std_dev"] = round(float(series.std()), 1)

    # Pass Rate calculation
    status_col = None
    for col in col_types["categorical"]:
        if any(k in col.lower() for k in ["status", "result", "outcome"]):
            status_col = col
            break

    if status_col:
        pass_count = df[status_col].astype(str).str.lower().str.contains("pass").sum()
        kpis["pass_rate"] = round((pass_count / len(df)) * 100, 1)
    elif score_col:
        # Check standard 40% cutoff if max marks can be inferred
        max_marks = 100
        if "Max_Marks" in df.columns:
            max_marks = df["Max_Marks"].iloc[0]
        cutoff = max_marks * 0.4
        pass_count = (df[score_col] >= cutoff).sum()
        kpis["pass_rate"] = round((pass_count / len(df)) * 100, 1)

    return kpis

def plot_grade_distribution(df: pd.DataFrame, cat_col: str) -> go.Figure:
    """Renders a donut chart of categorical distribution (e.g. Grades, Result Status)."""
    counts = df[cat_col].value_counts().reset_index()
    counts.columns = [cat_col, "Count"]

    fig = px.pie(
        counts,
        names=cat_col,
        values="Count",
        hole=0.45,
        title=f"Distribution by {cat_col}",
        color_discrete_sequence=THEME_COLORS
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hoverinfo='label+value+percent',
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    fig.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

def plot_score_histogram(df: pd.DataFrame, num_col: str) -> go.Figure:
    """Renders a distribution histogram with marginal box plot."""
    fig = px.histogram(
        df,
        x=num_col,
        nbins=25,
        marginal="box",
        title=f"Score Distribution ({num_col})",
        color_discrete_sequence=[ACCENT_BLUE],
        opacity=0.8
    )
    fig.update_layout(
        bargap=0.05,
        xaxis_title=num_col,
        yaxis_title="Student Count",
        margin=dict(t=40, b=20, l=20, r=20)
    )
    # Add vertical mean line
    mean_val = df[num_col].mean()
    fig.add_vline(
        x=mean_val,
        line_dash="dash",
        line_color=ACCENT_RED,
        annotation_text=f"Mean: {mean_val:.1f}",
        annotation_position="top left"
    )
    return fig

def plot_subject_performance(df: pd.DataFrame, group_col: str, num_col: str) -> go.Figure:
    """Renders average score comparison across groups (e.g. Subjects, Departments)."""
    summary = df.groupby(group_col)[num_col].agg(['mean', 'max', 'count']).reset_index()
    summary['mean'] = summary['mean'].round(1)
    summary = summary.sort_values(by='mean', ascending=True)

    fig = px.bar(
        summary,
        x='mean',
        y=group_col,
        orientation='h',
        text='mean',
        title=f"Average {num_col} by {group_col}",
        color='mean',
        color_continuous_scale="Blues",
        labels={'mean': f'Avg {num_col}', group_col: group_col}
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        coloraxis_showscale=False
    )
    return fig

def plot_box_distribution(df: pd.DataFrame, cat_col: str, num_col: str) -> go.Figure:
    """Renders box plots comparing score distributions across divisions or subjects."""
    fig = px.box(
        df,
        x=cat_col,
        y=num_col,
        color=cat_col,
        points="outliers",
        title=f"{num_col} Spread across {cat_col}",
        color_discrete_sequence=THEME_COLORS
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(t=40, b=20, l=20, r=20),
        xaxis_title=cat_col,
        yaxis_title=num_col
    )
    return fig

def plot_scatter_correlation(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None) -> go.Figure:
    """Renders a correlation scatter plot with optional regression trend line."""
    # Check if statsmodels is available for px trendline
    has_statsmodels = False
    try:
        import statsmodels
        has_statsmodels = True
    except ImportError:
        pass

    trendline_mode = "ols" if has_statsmodels else None

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col if color_col in df.columns else None,
        trendline=trendline_mode,
        title=f"Correlation: {x_col} vs {y_col}",
        color_discrete_sequence=THEME_COLORS,
        opacity=0.75
    )

    # If statsmodels not available, add simple numpy trendline
    if not has_statsmodels:
        clean_data = df[[x_col, y_col]].dropna()
        if len(clean_data) > 1 and pd.api.types.is_numeric_dtype(clean_data[x_col]) and pd.api.types.is_numeric_dtype(clean_data[y_col]):
            try:
                x_vals = clean_data[x_col].values
                y_vals = clean_data[y_col].values
                z = np.polyfit(x_vals, y_vals, 1)
                p = np.poly1d(z)
                x_line = np.linspace(x_vals.min(), x_vals.max(), 50)
                fig.add_trace(go.Scatter(
                    x=x_line,
                    y=p(x_line),
                    mode='lines',
                    name='Trend (OLS)',
                    line=dict(color=ACCENT_RED, dash='dash')
                ))
            except Exception:
                pass

    fig.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        xaxis_title=x_col,
        yaxis_title=y_col
    )
    return fig

def plot_performance_heatmap(df: pd.DataFrame, row_col: str, col_col: str) -> Optional[go.Figure]:
    """Generates cross-tabulation heatmap (e.g. Department vs Grade)."""
    cross_tab = pd.crosstab(df[row_col], df[col_col])
    if cross_tab.empty:
        return None

    fig = px.imshow(
        cross_tab,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Purples",
        title=f"Matrix: {row_col} vs {col_col}"
    )
    fig.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        xaxis_title=col_col,
        yaxis_title=row_col
    )
    return fig

def plot_time_trend(df: pd.DataFrame, date_col: str, num_col: str) -> go.Figure:
    """Renders timeline trend of scores/evaluations."""
    temp = df.copy()
    temp['_date_dt'] = pd.to_datetime(temp[date_col], errors='coerce')
    temp = temp.dropna(subset=['_date_dt'])
    trend = temp.groupby(temp['_date_dt'].dt.date)[num_col].agg(['mean', 'count']).reset_index()
    trend.columns = ['Date', 'Average_Score', 'Records']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend['Date'],
        y=trend['Average_Score'],
        mode='lines+markers',
        name='Avg Score',
        line=dict(color=ACCENT_BLUE, width=3),
        marker=dict(size=8)
    ))
    fig.update_layout(
        title=f"{num_col} Trend Over Time",
        xaxis_title="Date",
        yaxis_title=f"Avg {num_col}",
        margin=dict(t=40, b=20, l=20, r=20)
    )
    return fig

# ============================================================
# VISUALIZATION.PY
# Reads visualization_subset.csv (built by verification.py's
# finalize_pipeline()) and creates 5 charts using Polars + Plotly.
# Each chart is saved as its own clearly-named HTML file.
# ============================================================

import os
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Folder where this script lives - subset CSV comes from Output/master_data,
# chart outputs go into Output/charts
FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(FOLDER, "Output", "master_data", "visualization_subset.csv")

# Folder where all chart HTML files get saved
CHART_DIR = os.path.join(FOLDER, "Output", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


# Step 1: load the subset CSV into a Polars DataFrame
def load_subset():
    df = pl.read_csv(DATA_PATH, try_parse_dates=True)
    print(f"Loaded visualization_subset.csv: {df.height} rows, {len(df.columns)} columns")
    return df


# Small helper: some appointments have no doctor assigned (doctor_id was
# null or invalid), so doctor_name/specialization/hospital_branch can be
# null after the join in verification.py. Fill those in here so charts
# never break or show a blank category.
def fill_doctor_gaps(df):
    return df.with_columns([
        pl.col('specialization').fill_null('Not Assigned'),
        pl.col('doctor_name').fill_null('Not Assigned'),
        pl.col('hospital_branch').fill_null('Not Assigned'),
    ])


# ------------------------------------------------------------
# CHART 1: Hospital overview dashboard (4 small charts in 1 HTML)
#
# Placement logic (top row = OPERATIONS, bottom row = FINANCE):
#   Top-left:     Appointment Status        -> what's happening day-to-day
#   Top-right:    Appointments by Branch    -> where the daily load is
#   Bottom-left:  Revenue by Specialization -> where the money comes from
#   Bottom-right: Payment Status            -> is that money actually collected
# Grouping "operations" together and "finance" together (instead of
# alternating chart types) makes the dashboard easier to read top-to-bottom.
# ------------------------------------------------------------
def chart_1_dashboard(df):
    df = fill_doctor_gaps(df)

    status_counts = df.group_by('status').agg(pl.len().alias('count'))
    branch_counts = df.group_by('hospital_branch').agg(pl.len().alias('count')).sort('count', descending=True)
    revenue_by_spec = df.group_by('specialization').agg(pl.col('amount').sum().alias('revenue')).sort('revenue', descending=True)
    payment_counts = df.group_by('payment_status').agg(pl.len().alias('count'))

    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "domain"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "domain"}]],
        subplot_titles=("Appointment Status", "Appointments by Branch",
                         "Revenue by Specialization (Rs.)", "Payment Status")
    )

    # Qualitative palette so each bar/slice in a chart gets its own
    # distinct color instead of Plotly's single default trace color.
    palette = px.colors.qualitative.Set2

    fig.add_trace(
        go.Pie(labels=status_counts['status'].to_list(),
               values=status_counts['count'].to_list(),
               marker=dict(colors=palette),
               hole=0.4, name="Status"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=branch_counts['hospital_branch'].to_list(),
               y=branch_counts['count'].to_list(),
               marker=dict(color=palette[:len(branch_counts)]),
               name="Branch", showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(x=revenue_by_spec['specialization'].to_list(),
               y=revenue_by_spec['revenue'].to_list(),
               marker=dict(color=palette[:len(revenue_by_spec)]),
               name="Revenue", showlegend=False),
        row=2, col=1
    )
    fig.add_trace(
        go.Pie(labels=payment_counts['payment_status'].to_list(),
               values=payment_counts['count'].to_list(),
               marker=dict(colors=palette),
               hole=0.4, name="Payment"),
        row=2, col=2
    )

    # Each bar chart already labels its categories on the x-axis, so the
    # shared legend only needs to carry the two pie charts (status +
    # payment) - bars are hidden from it above via showlegend=False.
    fig.update_layout(
        title_text="Hospital Overview Dashboard - Operations (top) & Finance (bottom)",
        height=850, showlegend=True
    )

    path = os.path.join(CHART_DIR, "1_hospital_overview_dashboard.html")
    fig.write_html(path)
    print(f"Saved: {path}")


# ------------------------------------------------------------
# CHART 2: Sunburst - specialization -> doctor -> treatment_type
# Shows which doctor (under which specialization) gives which
# treatments the most. Click any ring to zoom in.
# ------------------------------------------------------------
def chart_2_specialization_doctor_treatment_sunburst(df):
    df = fill_doctor_gaps(df)

    # Sunburst needs every row to have a value at all 3 levels -
    # drop rows where treatment_type is missing/empty, otherwise
    # plotly raises "Non-leaves rows are not permitted".
    df = df.filter(
        pl.col("treatment_type").is_not_null()
        & (pl.col("treatment_type").str.strip_chars() != "")
    )

    fig = px.sunburst(
        df,
        path=['specialization', 'doctor_name', 'treatment_type'],
        title="Specialization -> Doctor -> Treatment Type"
    )

    path = os.path.join(CHART_DIR, "2_specialization_doctor_treatment_sunburst.html")
    fig.write_html(path)
    print(f"Saved: {path}")


# ------------------------------------------------------------
# CHART 3: Box plot - cost distribution per treatment_type
# Shows median cost, spread, and outliers for each treatment type.
# ------------------------------------------------------------
def chart_3_treatment_cost_distribution(df):
    fig = px.box(
        df,
        x='treatment_type',
        y='cost',
        title="Treatment Cost Distribution by Type"
    )

    path = os.path.join(CHART_DIR, "3_treatment_cost_distribution.html")
    fig.write_html(path)
    print(f"Saved: {path}")


# ------------------------------------------------------------
# CHART 4: Line chart - number of appointments per month
# ------------------------------------------------------------
def chart_4_monthly_appointment_trend(df):
    # Drop any appointment with a missing date - can't plot a trend point
    # for a date we don't have (should be rare/zero after cleaning.py)
    valid_dates = df.filter(pl.col('appointment_date').is_not_null())

    monthly = (
        valid_dates
        .with_columns(pl.col('appointment_date').dt.strftime('%Y-%m').alias('month'))
        .group_by('month')
        .agg(pl.len().alias('appointment_count'))
        .sort('month')
    )

    fig = px.line(
        monthly,
        x='month',
        y='appointment_count',
        markers=True,
        title="Appointments per Month"
    )

    path = os.path.join(CHART_DIR, "4_monthly_appointment_trend.html")
    fig.write_html(path)
    print(f"Saved: {path}")


# ------------------------------------------------------------
# CHART 5: Bar chart - no-show rate (%) per specialization
# This is the most "actionable" chart: it tells you which
# specialization has the worst no-show problem.
# ------------------------------------------------------------
def chart_5_noshow_rate_by_specialization(df):
    df = fill_doctor_gaps(df)

    rate_df = (
        df.group_by('specialization')
          .agg([
              (pl.col('status') == 'No-show').sum().alias('no_show_count'),
              pl.len().alias('total_appointments'),
          ])
          .with_columns(
              (pl.col('no_show_count') / pl.col('total_appointments') * 100)
                .round(1).alias('no_show_rate_pct')
          )
          .sort('no_show_rate_pct', descending=True)
    )

    fig = px.bar(
        rate_df,
        x='specialization',
        y='no_show_rate_pct',
        title="No-show Rate (%) by Specialization",
        text='no_show_rate_pct'
    )
    fig.update_traces(texttemplate='%{text}%', textposition='outside')

    path = os.path.join(CHART_DIR, "5_noshow_rate_by_specialization.html")
    fig.write_html(path)
    print(f"Saved: {path}")


# ------------------------------------------------------------
# Run everything: python visualization.py
# ------------------------------------------------------------
if __name__ == "__main__":

    df = load_subset()

    chart_1_dashboard(df)
    chart_2_specialization_doctor_treatment_sunburst(df)
    chart_3_treatment_cost_distribution(df)
    chart_4_monthly_appointment_trend(df)
    chart_5_noshow_rate_by_specialization(df)

    print(f"\nAll 5 charts saved in: {CHART_DIR}/")

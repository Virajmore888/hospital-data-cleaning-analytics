# ============================================================
# INSIGHTS.PY
# Reads visualization_subset.csv (built by verification.py's
# finalize_pipeline()) and answers business questions.
# Loading/filtering/grouping is done with Polars (matching the
# rest of the pipeline). Every actual statistic (mean, median,
# correlation, argmax, etc.) is computed with NumPy on the
# .to_numpy() arrays pulled out of Polars - no pandas anywhere.
# Prints each answer and saves a full report to insights_report.txt.
# ============================================================

import os
from datetime import datetime
import numpy as np
import polars as pl

FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(FOLDER, "Output", "master_data", "visualization_subset.csv")
REPORT_DIR = os.path.join(FOLDER, "Output", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
REPORT_PATH = os.path.join(REPORT_DIR, "insights_report.txt")


def load_insights_subset():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"visualization_subset.csv not found at {DATA_PATH}\n"
            "Run verification.py -> finalize_pipeline() first to generate it."
        )
    df = pl.read_csv(DATA_PATH, try_parse_dates=True)
    return df


def q1_noshow_rate(df):
    status = df['status'].to_numpy()
    rate = np.mean(status == 'No-show') * 100
    line = (
        f"Q1. What is the overall no-show rate?\n"
        f"-> {rate:.2f}% of all appointments ended up as a no-show."
    )
    return line, rate


def q2_specialization_highest_noshow(df):
    valid = df.drop_nulls(subset=['specialization'])
    grouped = valid.group_by('specialization').agg(
        (pl.col('status') == 'No-show').mean().alias('noshow_rate')
    )
    spec_names = grouped['specialization'].to_numpy()
    spec_rates = grouped['noshow_rate'].to_numpy() * 100
    top_idx = np.argmax(spec_rates)

    line = (
        f"Q2. Which specialization has the highest no-show rate?\n"
        f"-> {spec_names[top_idx]} has the highest no-show rate at {spec_rates[top_idx]:.2f}%."
    )
    return line, (spec_names[top_idx], spec_rates[top_idx])


def q3_cost_gap_by_payment_status(df):
    valid = df.drop_nulls(subset=['cost', 'payment_status'])
    paid_cost = valid.filter(pl.col('payment_status') == 'Paid')['cost'].to_numpy()
    pending_cost = valid.filter(pl.col('payment_status') == 'Pending')['cost'].to_numpy()

    paid_mean = np.mean(paid_cost)
    pending_mean = np.mean(pending_cost)
    paid_median = np.median(paid_cost)
    pending_median = np.median(pending_cost)
    gap = pending_mean - paid_mean

    direction = "higher" if gap > 0 else "lower"
    line = (
        f"Q3. Is there a cost gap between paid and pending treatments?\n"
        f"-> Pending treatments cost {abs(gap):,.2f} on average {direction} than paid ones.\n"
        f"   Paid: mean={paid_mean:,.2f}, median={paid_median:,.2f}\n"
        f"   Pending: mean={pending_mean:,.2f}, median={pending_median:,.2f}"
    )
    return line, gap


def q4_average_treatment_cost(df):
    valid = df.drop_nulls(subset=['cost'])
    all_cost = valid['cost'].to_numpy()
    overall_avg = np.mean(all_cost)

    type_valid = valid.drop_nulls(subset=['treatment_type'])
    grouped = type_valid.group_by('treatment_type').agg(
        pl.col('cost').mean().alias('avg_cost')
    )
    type_names = grouped['treatment_type'].to_numpy()
    type_avgs = grouped['avg_cost'].to_numpy()
    top_idx = np.argmax(type_avgs)

    line = (
        f"Q4. What is the average treatment cost, and which treatment type costs the most?\n"
        f"-> Overall average treatment cost is {overall_avg:,.2f}.\n"
        f"   {type_names[top_idx]} is the most expensive treatment type on average, at {type_avgs[top_idx]:,.2f}."
    )
    return line, (overall_avg, type_names[top_idx], type_avgs[top_idx])


def q5_noshow_by_gender(df):
    valid = df.drop_nulls(subset=['gender'])
    grouped = valid.group_by('gender').agg(
        (pl.col('status') == 'No-show').mean().alias('noshow_rate')
    )
    gender_names = grouped['gender'].to_numpy()
    gender_rates = grouped['noshow_rate'].to_numpy() * 100
    top_idx = np.argmax(gender_rates)

    lines = ["Q5. Is the no-show rate different between genders?"]
    for g, r in zip(gender_names, gender_rates):
        lines.append(f"   {g}: {r:.2f}% no-show rate")
    lines.append(f"-> {gender_names[top_idx]} patients no-show more often, at {gender_rates[top_idx]:.2f}%.")
    line = "\n".join(lines)
    return line, dict(zip(gender_names, gender_rates))


def q6_cost_vs_age_link(df):
    # Correlation between doctor experience isn't in this subset directly,
    # so instead we check cost vs. patient age - a commonly asked business
    # question (do older patients get costlier treatments?).
    valid = df.drop_nulls(subset=['cost', 'date_of_birth'])
    today = pl.lit(datetime.now().date())
    valid = valid.with_columns(
        ((today - pl.col('date_of_birth')).dt.total_days() / 365.25).alias('age_years')
    )

    age_years = valid['age_years'].to_numpy()
    cost = valid['cost'].to_numpy()

    ok = ~np.isnan(age_years) & ~np.isnan(cost)
    corr_matrix = np.corrcoef(age_years[ok], cost[ok])
    corr = corr_matrix[0, 1]

    if abs(corr) < 0.1:
        strength = "almost no link"
    elif abs(corr) < 0.3:
        strength = "a weak link"
    elif abs(corr) < 0.6:
        strength = "a moderate link"
    else:
        strength = "a strong link"

    line = (
        f"Q6. Do older patients receive costlier treatments?\n"
        f"-> The correlation between patient age and treatment cost is {corr:.2f}.\n"
        f"   This means there is {strength} between the two."
    )
    return line, corr


def q7_highest_revenue_branch(df):
    valid = df.drop_nulls(subset=['amount', 'hospital_branch'])
    grouped = valid.group_by('hospital_branch').agg(
        pl.col('amount').sum().alias('revenue')
    )
    branch_names = grouped['hospital_branch'].to_numpy()
    branch_revenue = grouped['revenue'].to_numpy()
    top_idx = np.argmax(branch_revenue)

    line = (
        f"Q7. Which hospital branch generates the most revenue?\n"
        f"-> {branch_names[top_idx]} generates the highest revenue at {branch_revenue[top_idx]:,.2f}."
    )
    return line, (branch_names[top_idx], branch_revenue[top_idx])


def q8_payment_failure_vs_cost(df):
    valid = df.drop_nulls(subset=['cost', 'payment_status'])
    failed_cost = valid.filter(pl.col('payment_status') == 'Failed')['cost'].to_numpy()
    ok_cost = valid.filter(pl.col('payment_status') != 'Failed')['cost'].to_numpy()

    failed_avg = np.mean(failed_cost) if failed_cost.size > 0 else float('nan')
    ok_avg = np.mean(ok_cost)

    if failed_cost.size == 0:
        conclusion = "There are no failed payments in this data, so no comparison can be made."
        failed_line = "Failed payments: none found in this data."
    elif failed_avg > ok_avg:
        conclusion = "Failed payments tend to be for costlier treatments. Higher bills may be harder to collect."
        failed_line = f"Failed payments: {failed_avg:.2f} avg cost."
    else:
        conclusion = "Failed payments are not linked to higher treatment cost here."
        failed_line = f"Failed payments: {failed_avg:.2f} avg cost."

    line = (
        f"Q8. Are failed payments linked to higher treatment cost?\n"
        f"-> {failed_line}\n"
        f"   Paid/Pending payments: {ok_avg:.2f} avg cost.\n"
        f"   {conclusion}"
    )
    return line, (failed_avg, ok_avg)


def run_all_insights():
    df = load_insights_subset()

    header = "=" * 70 + "\nHEALTHCARE INSIGHTS REPORT\n" + "=" * 70 + "\n"
    footer = "\n" + "=" * 70 + f"\nReport generated from {df.height} appointment records.\n" + "=" * 70

    questions = [
        q1_noshow_rate,
        q2_specialization_highest_noshow,
        q3_cost_gap_by_payment_status,
        q4_average_treatment_cost,
        q5_noshow_by_gender,
        q6_cost_vs_age_link,
        q7_highest_revenue_branch,
        q8_payment_failure_vs_cost,
    ]

    all_lines = [header]
    for fn in questions:
        line, _ = fn(df)
        print(line)
        print()
        all_lines.append(line)
        all_lines.append("")

    all_lines.append(footer)
    print(footer)

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(all_lines))

    print(f"\nSaved report to: {REPORT_PATH}")


if __name__ == "__main__":
    run_all_insights()

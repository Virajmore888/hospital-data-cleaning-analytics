# Import required libraries
import polars as pl
import matplotlib
matplotlib.use('Agg')  # Save plots to file instead of opening a window (safe for mobile)
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

# Folder this script lives in, used to anchor DATA_DIR/OUTPUT_DIR so the
# script works the same regardless of the directory it's run from
FOLDER = os.path.dirname(os.path.abspath(__file__))

# Folder where the messy CSV files live
DATA_DIR = os.path.join(FOLDER, "data")

# Folder where all plots will be saved
OUTPUT_DIR = os.path.join(FOLDER, "Output", "eda_plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# All tables from the schema (file name without .csv)
TABLES = ['patients', 'doctors', 'appointments', 'treatments', 'billing']

# Columns ending with "_id" are identifiers, not real numeric data
ID_SUFFIXES = ('_id',)

# Known messy date formats present in this data (used only for the
# business_logic_checks date comparisons - see note near that function)
_DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"]


# Function to load any table into a DataFrame
# (SQL query replaced with reading the matching CSV file)
def get_table(table_name):
    path = os.path.join(DATA_DIR, f"{table_name}.csv")
    df = pl.read_csv(path, infer_schema_length=10000, try_parse_dates=False)
    return df


# Vectorized replacement for the old row-by-row Python date parser
# (used only inside business_logic_checks, not during EDA display).
# For each known format, ask Polars to parse the WHOLE column at once
# (strict=False -> unparseable values become null instead of raising).
# coalesce() takes the first non-null result across all format attempts,
# per row - so no Python-level loop over individual row values anymore.
def _parse_messy_date_column(series):
    attempts = [series.str.to_date(fmt, strict=False) for fmt in _DATE_FORMATS]
    return pl.select(pl.coalesce(attempts)).to_series()


# Function to run statistical EDA on a table
def data_exploration(df, name):

    print("=" * 70)
    print("NOW PROCESSING TABLE:", name)
    print("=" * 70)

    # Show first 5 rows
    print("\nFirst 5 Rows")
    print(df.head())

    # Show column names and data types (Polars equivalent of df.info())
    print("\nSchema (column -> dtype)")
    print(df.schema)

    # Show number of rows and columns
    print("\nShape:", df.shape)

    # Show estimated memory usage (Polars equivalent of memory_usage(deep=True))
    print("\nEstimated Memory (MB):", round(df.estimated_size("mb"), 2))

    # Show all column names
    print("\nColumn Names:", df.columns)

    # Show missing values count and percentage
    print("\nMissing Values (count + percentage)")
    null_counts = df.null_count().row(0, named=True)
    for col, cnt in null_counts.items():
        if cnt > 0:
            pct = round((cnt / df.height) * 100, 2)
            print(f"  {col}: missing_count={cnt}, missing_pct={pct}")
    print("Total Missing Values:", sum(null_counts.values()))

    # Show number of duplicate rows (extra rows beyond the unique set,
    # same meaning as pandas df.duplicated().sum())
    dup_count = df.height - df.unique(keep="first").height
    print("\nDuplicate Rows:", dup_count)

    # Show number of unique values per column
    print("\nUnique Values per Column")
    nunique_row = df.select(pl.all().n_unique()).row(0, named=True)
    for col, cnt in nunique_row.items():
        print(f"  {col}: {cnt}")

    # Separate columns into groups: id, numeric, date, category
    id_cols = [c for c in df.columns if c.endswith(ID_SUFFIXES)]
    numeric_cols = [c for c, dt in df.schema.items()
                     if dt.is_numeric() and c not in id_cols]
    date_cols = [c for c, dt in df.schema.items()
                  if dt in (pl.Date, pl.Datetime)]
    cat_cols = [c for c, dt in df.schema.items()
                 if dt == pl.Utf8 and c not in date_cols]

    # Show descriptive statistics only for real numeric columns (not id columns)
    if numeric_cols:
        print("\nDescriptive Statistics (numeric columns, id columns excluded)")
        print(df.select(numeric_cols).describe())

    # Go through each column one by one for detailed analysis
    print("\nColumn Wise Analysis")
    for col in df.columns:

        series = df[col]
        print("\n--- Column:", col, "---")
        print("Data Type:", series.dtype)
        print("Missing Values:", series.null_count())

        # ID column: skip statistics, not meaningful
        if col in id_cols:
            print("Type: ID column, skipping statistics")

        # Date column: show earliest, latest, and range
        elif col in date_cols:
            print("Min Date:", series.min())
            print("Max Date:", series.max())
            print("Range (days):", (series.max() - series.min()).days)

        # Category column: show unique values and counts
        # (Note: on this raw messy data, columns like status/gender/payment_status
        # will show messy variants here - e.g. "Paid", "paid", "PAID" as separate
        # categories. That messiness is EXPECTED at this stage; it gets fixed later
        # in cleaning.py, not here.)
        elif col in cat_cols:
            n_unique = series.n_unique()
            print("Unique Count:", n_unique)
            vc = series.value_counts().sort("count", descending=True)
            if n_unique <= 30:
                print("Value Counts:")
                print(vc)
            else:
                print("Too many unique values to display fully")
                print("Top 5 Value Counts:")
                print(vc.head(5))

        # Numeric column: show summary stats and outlier count
        elif col in numeric_cols:
            print("Min:", series.min())
            print("Max:", series.max())
            print("Mean:", round(series.mean(), 2) if series.mean() is not None else None)
            print("Median:", series.median())
            print("Std Dev:", round(series.std(), 2) if series.std() is not None else None)

            # Detect outliers using the IQR method
            Q1 = series.quantile(0.25, interpolation="linear")
            Q3 = series.quantile(0.75, interpolation="linear")
            if Q1 is not None and Q3 is not None:
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                outliers = series.filter((series < lower) | (series > upper))
                print("Outliers (IQR method):", outliers.len())

        else:
            print("Min:", series.min())
            print("Max:", series.max())


# Function to create visual plots for a table
def visualize_table(df, name):

    print(f"\n[VISUALIZING] {name}")

    id_cols = [c for c in df.columns if c.endswith(ID_SUFFIXES)]
    numeric_cols = [c for c, dt in df.schema.items()
                     if dt.is_numeric() and c not in id_cols]
    cat_cols = [c for c, dt in df.schema.items() if dt == pl.Utf8]

    # Create a separate folder for this table's plots
    table_dir = os.path.join(OUTPUT_DIR, name)
    os.makedirs(table_dir, exist_ok=True)

    # Plot histogram and boxplot for each numeric column
    for col in numeric_cols:
        values = df[col].drop_nulls().to_numpy()
        if values.size == 0:
            continue

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        sns.histplot(values, kde=True, ax=axes[0])
        axes[0].set_title(f"{col} - Distribution")

        sns.boxplot(x=values, ax=axes[1])
        axes[1].set_title(f"{col} - Outliers")

        plt.tight_layout()
        plt.savefig(os.path.join(table_dir, f"{col}_numeric.png"))
        plt.close()

    # Plot count of values for low-cardinality category columns only
    for col in cat_cols:
        n_unique = df[col].n_unique()
        if n_unique == 0 or n_unique > 20:
            continue  # skip columns like email, phone_number, address (too many unique values)

        vc = df[col].value_counts().sort("count", descending=True)
        categories = vc[col].to_list()
        counts = vc["count"].to_list()

        plt.figure(figsize=(8, 4))
        sns.barplot(x=counts, y=categories)
        plt.title(f"{col} - Value Counts")
        plt.tight_layout()
        plt.savefig(os.path.join(table_dir, f"{col}_categorical.png"))
        plt.close()

    # Plot correlation heatmap if there are at least 2 numeric columns
    if len(numeric_cols) >= 2:
        corr_df = df.select(numeric_cols).corr()
        corr_matrix = corr_df.to_numpy()

        plt.figure(figsize=(6, 5))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f",
                    xticklabels=numeric_cols, yticklabels=numeric_cols)
        plt.title(f"{name} - Correlation Matrix")
        plt.tight_layout()
        plt.savefig(os.path.join(table_dir, "correlation_matrix.png"))
        plt.close()

    print(f"Plots saved in: {table_dir}/")


# Function to check for invalid foreign key references (orphan records)
def check_foreign_key(child_df, child_col, parent_df, parent_col, child_name, parent_name):
    child_ids = set(child_df[child_col].drop_nulls().to_list())
    parent_ids = set(parent_df[parent_col].drop_nulls().to_list())
    orphans = child_ids - parent_ids

    print(f"\n[FOREIGN KEY CHECK] {child_name}.{child_col} -> {parent_name}.{parent_col}")
    print("Invalid references found:", len(orphans))
    if orphans:
        print("Sample invalid values:", list(orphans)[:10])


# Function to check business logic rules based on the schema
# NOTE: this merges tables temporarily, in-memory, only to cross-check values -
# it does NOT create the real master CSV. The actual join happens later,
# in a separate step, only after every individual CSV has passed verification.py.
# NOTE 2: date columns here are still raw messy text (mixed formats), so this
# function uses the vectorized _parse_messy_date_column() helper above
# (coalesce over multiple format attempts) instead of relying on Polars'
# strict single-format date parsing.
# Needs a dictionary of DataFrames, build it manually when needed:
# dfs = {"patients": get_table("patients"), "doctors": get_table("doctors"),
#        "appointments": get_table("appointments"), "treatments": get_table("treatments"),
#        "billing": get_table("billing")}
def business_logic_checks(dfs):

    print("\n" + "=" * 70)
    print("BUSINESS LOGIC CHECKS")
    print("=" * 70)

    pat = dfs['patients']
    doc = dfs['doctors']
    appt = dfs['appointments']
    treat = dfs['treatments']
    bill = dfs['billing']

    # Check 1: billing amount should match the linked treatment's cost
    merged = bill.join(treat, on='treatment_id', how='left')
    merged = merged.with_columns([
        pl.col('amount').cast(pl.Float64, strict=False).alias('_amount_num'),
        pl.col('cost').cast(pl.Float64, strict=False).alias('_cost_num'),
    ])
    mismatch = merged.filter(
        pl.col('_amount_num').is_not_null()
        & pl.col('_cost_num').is_not_null()
        & (pl.col('_amount_num') != pl.col('_cost_num'))
    )
    print("\nBilling rows where amount != linked treatment cost:", mismatch.height)

    # Check 2: treatment cost should never be negative
    treat_cost_num = treat.with_columns(
        pl.col('cost').cast(pl.Float64, strict=False).alias('_cost_num')
    )
    negative_cost = treat_cost_num.filter(pl.col('_cost_num') < 0)
    print("Treatments with negative cost:", negative_cost.height)

    # Check 3: appointment_date should not fall after treatment_date for the same appointment
    joined = appt.join(treat, on='appointment_id', how='inner')
    joined = joined.with_columns([
        _parse_messy_date_column(joined['appointment_date']).alias('_a_date'),
        _parse_messy_date_column(joined['treatment_date']).alias('_t_date'),
    ])
    bad_order_count = joined.filter(
        pl.col('_a_date').is_not_null()
        & pl.col('_t_date').is_not_null()
        & (pl.col('_t_date') < pl.col('_a_date'))
    ).height
    print("Treatments dated before their own appointment:", bad_order_count)

    # Check 4: doctor_id on an appointment should exist in the doctors table
    known_doctors = set(doc['doctor_id'].drop_nulls().to_list())
    invalid_doctor = appt.filter(
        pl.col('doctor_id').is_not_null()
        & ~pl.col('doctor_id').is_in(known_doctors)
    )
    print("Appointments with a doctor_id not found in doctors table:", invalid_doctor.height)

    # Check 5: patient date_of_birth should not be in the future or unrealistically old
    today = pl.lit(datetime.now().date())
    dob_parsed = pat.with_columns(
        _parse_messy_date_column(pat['date_of_birth']).alias('_dob')
    )
    bad_dob_count = dob_parsed.filter(
        pl.col('_dob').is_not_null()
        & ((pl.col('_dob') > today)
           | (((today - pl.col('_dob')).dt.total_days() / 365.25) > 110))
    ).height
    print("Patients with an invalid date_of_birth (future or >110 years old):", bad_dob_count)


# ============================================================
# SECTION: CALL TABLES ONE BY ONE (manual, no auto loop)
# Prints the table name, then runs data_exploration() +
# visualize_table() for JUST that one table.
# Usage:  run_eda('patients')
# ============================================================

def run_eda(table_name):
    print("\n" + "#" * 70)
    print(f"# TABLE: {table_name}")
    print("#" * 70)

    df = get_table(table_name)
    data_exploration(df, table_name)
    visualize_table(df, table_name)

    return df


# Main program: only sets up tools, does NOT auto-run any table
# Run this file with: python -i EDA.py
# Then call run_eda('table_name') for whichever table you want
if __name__ == "__main__":

    print("Setup done. Available tables:", TABLES)
    print("\nHow to use (call one table at a time yourself):")
    print("  df = run_eda('patients')")
    print("  df = run_eda('appointments')")
    print("\nFor foreign key / business logic checks, build a dict manually:")
    print("  dfs = {'patients': get_table('patients'), 'doctors': get_table('doctors'), "
          "'appointments': get_table('appointments'), 'treatments': get_table('treatments'), "
          "'billing': get_table('billing')}")
    print("  business_logic_checks(dfs)")

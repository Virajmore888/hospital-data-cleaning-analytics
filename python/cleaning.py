# Import required libraries
import os
import re
import polars as pl
from datetime import datetime

# Folder where the messy CSV files live (same as EDA.py)
DATA_DIR = "data"

# Folder where cleaned CSVs get saved (Output/cleaned_data next to this
# script — same folder verification.py will read from)
FOLDER = os.path.dirname(os.path.abspath(__file__))
CLEANED_DIR = os.path.join(FOLDER, "Output", "cleaned_data")
os.makedirs(CLEANED_DIR, exist_ok=True)

# All tables from the schema, in an order that respects dependencies
# (doctors before appointments, treatments before billing - see notes below)
TABLES = ['doctors', 'patients', 'treatments', 'appointments', 'billing']

# Known messy date formats present in this data (same list as EDA.py)
_DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"]


# Function to load any table into a DataFrame
# (SQL query replaced with reading the matching CSV file)
def get_table(table_name):
    path = os.path.join(DATA_DIR, f"{table_name}.csv")
    df = pl.read_csv(path, infer_schema_length=10000, try_parse_dates=False)
    return df


# Function to save a cleaned DataFrame as CSV
# Filename pattern matches what verification.py expects: <table>_cleaned.csv
def save_cleaned_csv(df, table_name):
    path = os.path.join(CLEANED_DIR, f"{table_name}_cleaned.csv")
    df.write_csv(path)
    print(f"Saved: {path} ({df.height} rows)")
    return path


# Function to optimize memory usage of a DataFrame
# This runs AFTER cleaning, so wrong values don't get locked into small dtypes
def optimize_memory(df):

    before_mb = df.estimated_size("mb")

    exprs = []
    for col, dtype in df.schema.items():

        # Downcast numeric columns to the smallest type that fits the values
        if dtype.is_integer() or dtype.is_float():
            exprs.append(pl.col(col).shrink_dtype().alias(col))

        # Convert text columns with few unique values into Categorical type
        # (saves a lot of memory, e.g. gender, status, specialization)
        elif dtype == pl.Utf8:
            n_unique = df[col].n_unique()
            n_total = df.height
            if n_total > 0 and (n_unique / n_total) < 0.5:
                exprs.append(pl.col(col).cast(pl.Categorical).alias(col))

    if exprs:
        df = df.with_columns(exprs)

    after_mb = df.estimated_size("mb")

    print(f"Memory before: {round(before_mb, 3)} MB")
    print(f"Memory after:  {round(after_mb, 3)} MB")
    print(f"Reduced by:    {round(before_mb - after_mb, 3)} MB")

    return df


# Function to standardize text columns (fix casing and extra spaces)
def standardize_text(df, columns):
    exprs = []
    for col in columns:
        if col in df.columns:
            exprs.append(
                pl.col(col).cast(pl.Utf8).str.strip_chars().str.to_titlecase().alias(col)
            )
    if exprs:
        df = df.with_columns(exprs)
    return df


# Vectorized replacement for the old row-by-row Python date parser.
# For each known format, ask Polars to parse the WHOLE column at once
# (strict=False -> unparseable values become null instead of raising).
# coalesce() then takes the first non-null result across all format
# attempts, per row - so a row parses successfully as soon as ANY
# format matches it. No Python-level loop over rows anymore.
def standardize_date_column(df, col):
    if col in df.columns:
        attempts = [
            pl.col(col).str.to_date(fmt, strict=False)
            for fmt in _DATE_FORMATS
        ]
        df = df.with_columns(pl.coalesce(attempts).alias(col))
    return df


# Small helper: keeps only digits from a phone number, and trims a
# leading country code down to the last 10 digits (e.g. +91 prefix)
def _clean_phone(value):
    if value is None:
        return None
    digits = re.sub(r'[^0-9]', '', str(value))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if digits else None


# Small helper: EDA found unrealistic date_of_birth values (future dates,
# 1899 entries). Cannot guess the real DOB, so these get nulled out instead
# of silently kept - same philosophy as "missing email -> flag, don't fake it"
def _validate_dob(d):
    if d is None:
        return None
    today = datetime.now().date()
    if d > today:
        return None
    age_years = (today - d).days / 365.25
    if age_years > 110:
        return None
    return d


# Function to clean the doctors table
def clean_doctors(df):

    print("\nCleaning: doctors")

    # Fix casing (dermatology / DERMATOLOGY -> Dermatology)
    df = standardize_text(df, ['specialization', 'first_name', 'last_name'])

    # Strip stray whitespace picked up around branch names
    df = df.with_columns(pl.col('hospital_branch').str.strip_chars().alias('hospital_branch'))

    # years_experience sometimes has " yrs" text mixed in with the number
    df = df.with_columns(
        pl.col('years_experience').cast(pl.Utf8)
          .str.replace_all(r'[^0-9]', '')
          .cast(pl.Int64, strict=False)
          .alias('years_experience')
    )

    # Missing phone number: cannot guess it, flag clearly instead of blank
    df = df.with_columns(pl.col('phone_number').fill_null('MISSING'))

    df = df.unique(keep='first', maintain_order=True)

    return df


# Function to clean the patients table
def clean_patients(df):

    print("\nCleaning: patients")

    # Fix gender abbreviations/casing (M/m/male -> Male, F/f/female -> Female)
    gender_map = {'M': 'Male', 'F': 'Female', 'm': 'Male', 'f': 'Female',
                  'male': 'Male', 'female': 'Female'}
    df = df.with_columns(pl.col('gender').replace(gender_map).alias('gender'))

    # Strip whitespace, fix casing on names and insurance provider
    df = standardize_text(df, ['first_name', 'last_name', 'insurance_provider'])

    # Standardize date_of_birth and registration_date into one format,
    # then null out any date_of_birth that's clearly wrong (future / 110+ yrs)
    df = standardize_date_column(df, 'date_of_birth')
    df = standardize_date_column(df, 'registration_date')
    df = df.with_columns(
        pl.col('date_of_birth').map_elements(_validate_dob, return_dtype=pl.Date).alias('date_of_birth')
    )

    # Clean up phone number formatting (dashes/spaces/+91/brackets -> digits only)
    df = df.with_columns(
        pl.col('contact_number').map_elements(_clean_phone, return_dtype=pl.Utf8).alias('contact_number')
    )
    df = df.with_columns(pl.col('contact_number').fill_null('MISSING'))

    # Missing email/address: cannot guess them, flag clearly instead of blank
    df = df.with_columns(pl.col('email').str.to_lowercase().alias('email'))
    df = df.with_columns([
        pl.col('email').fill_null('MISSING'),
        pl.col('address').fill_null('MISSING'),
    ])

    df = df.unique(keep='first', maintain_order=True)

    return df


# Function to clean the treatments table
def clean_treatments(df):

    print("\nCleaning: treatments")

    # Fix casing, fill missing treatment_type with a clear label
    df = standardize_text(df, ['treatment_type', 'description'])
    df = df.with_columns(pl.col('treatment_type').fill_null('Unknown'))

    # cost sometimes has "$" and "," in it - strip those, then convert to number
    df = df.with_columns(
        pl.col('cost').cast(pl.Utf8)
          .str.replace_all(r'[^0-9.\-]', '')
          .cast(pl.Float64, strict=False)
          .alias('cost')
    )

    # cost should never be negative (EDA found some) - likely a sign entry
    # error, so take the absolute value instead of dropping the row
    df = df.with_columns(pl.col('cost').abs().alias('cost'))

    # Missing cost: fill using the median cost of the same treatment_type
    df = df.with_columns(
        pl.col('cost').fill_null(pl.col('cost').median().over('treatment_type'))
    )
    # If still missing (treatment_type had no other cost data), use overall median
    df = df.with_columns(pl.col('cost').fill_null(pl.col('cost').median()))

    df = standardize_date_column(df, 'treatment_date')

    df = df.unique(keep='first', maintain_order=True)

    return df


# Function to clean the appointments table
# Needs the already-cleaned doctors_df to check which doctor_id values
# actually exist (same pattern as HR's employees needing jobs_df)
def clean_appointments(df, doctors_df):

    print("\nCleaning: appointments")

    # Fix status typos/casing into 4 canonical categories
    status_map = {
        'scheduled': 'Scheduled', 'SCHEDULED': 'Scheduled',
        'No Show': 'No-show', 'no-show': 'No-show', 'NoShow': 'No-show',
        'Canceled': 'Cancelled', 'cancelled': 'Cancelled',
        'completed': 'Completed', 'COMPLETED': 'Completed', 'Done': 'Completed',
    }
    df = df.with_columns(pl.col('status').replace(status_map).alias('status'))

    # doctor_id pointing to a doctor that doesn't exist (data entry typo,
    # e.g. "D999") can't be trusted - null it out rather than keep a wrong link.
    # doctor_id that's genuinely blank stays blank (not-yet-assigned is valid).
    known_doctors = set(doctors_df['doctor_id'].drop_nulls().to_list())
    df = df.with_columns(
        pl.when(pl.col('doctor_id').is_not_null() & ~pl.col('doctor_id').is_in(known_doctors))
        .then(None)
        .otherwise(pl.col('doctor_id'))
        .alias('doctor_id')
    )

    # Missing reason_for_visit: some rows are truly blank (null), others have
    # the literal text "N/A" instead of being blank - both mean the same
    # thing here, so normalize both into one clear label
    df = df.with_columns(
        pl.when(pl.col('reason_for_visit').is_null() | (pl.col('reason_for_visit') == 'N/A'))
        .then(pl.lit('Not Specified'))
        .otherwise(pl.col('reason_for_visit'))
        .alias('reason_for_visit')
    )
    df = df.with_columns(pl.col('appointment_time').fill_null('MISSING'))

    df = standardize_date_column(df, 'appointment_date')

    df = df.unique(keep='first', maintain_order=True)

    return df


# Function to clean the billing table
# Needs the already-cleaned treatments_df to fix amount vs cost mismatches
# (same pattern as HR's employees needing jobs_df for the salary range check)
def clean_billing(df, treatments_df):

    print("\nCleaning: billing")

    # Fix payment_status casing into canonical categories
    pay_map = {'paid': 'Paid', 'PAID': 'Paid',
               'pending': 'Pending', 'PENDING': 'Pending',
               'failed': 'Failed', 'FAILED': 'Failed'}
    df = df.with_columns(pl.col('payment_status').replace(pay_map).alias('payment_status'))
    df = df.with_columns(pl.col('payment_method').fill_null('MISSING'))

    # amount sometimes has "Rs." and "," in it - strip those, then convert to number
    df = df.with_columns(
        pl.col('amount').cast(pl.Utf8)
          .str.replace_all(r'[^0-9.\-]', '')
          .cast(pl.Float64, strict=False)
          .alias('amount')
    )

    df = standardize_date_column(df, 'bill_date')

    # EDA found billing.amount not always matching the linked treatment's cost.
    # The treatment cost is the source of truth, so correct any mismatches.
    df = df.join(
        treatments_df.select(['treatment_id', 'cost']), on='treatment_id', how='left'
    )
    df = df.with_columns(
        pl.when(pl.col('cost').is_not_null() & pl.col('amount').is_not_null()
                & (pl.col('amount') != pl.col('cost')))
        .then(pl.col('cost'))
        .otherwise(pl.col('amount'))
        .alias('amount')
    )
    df = df.drop('cost')

    df = df.unique(keep='first', maintain_order=True)

    return df


# ============================================================
# SECTION: CALL TABLES ONE BY ONE (manual, no auto loop)
# Prints the table name, cleans that ONE table, optimizes
# memory, and saves it via save_cleaned_csv().
# Usage:
#   doc_df   = run_cleaning('doctors')
#   pat_df   = run_cleaning('patients')
#   treat_df = run_cleaning('treatments')
#   appt_df  = run_cleaning('appointments', doctors_df=doc_df)
#   bill_df  = run_cleaning('billing', treatments_df=treat_df)
# ============================================================

CLEAN_FUNCS = {
    'doctors': clean_doctors,
    'patients': clean_patients,
    'treatments': clean_treatments,
}


def run_cleaning(table_name, doctors_df=None, treatments_df=None):
    print("\n" + "#" * 70)
    print(f"# TABLE: {table_name}")
    print("#" * 70)

    df = get_table(table_name)

    if table_name == 'appointments':
        # appointments cleaning needs an already-cleaned doctors_df to check
        # which doctor_id values are real. If not passed in, clean it ourselves.
        if doctors_df is None:
            doctors_df = run_cleaning('doctors')
        df = clean_appointments(df, doctors_df)
    elif table_name == 'billing':
        # billing cleaning needs an already-cleaned treatments_df for the
        # amount vs cost check. If not passed in, clean it ourselves.
        if treatments_df is None:
            treatments_df = run_cleaning('treatments')
        df = clean_billing(df, treatments_df)
    else:
        df = CLEAN_FUNCS[table_name](df)

    df = optimize_memory(df)
    save_cleaned_csv(df, table_name)

    return df


# Main program: only sets up tools, does NOT auto-run any table
# Run this file with: python -i cleaning.py
# Then call run_cleaning('table_name') for whichever table you want
if __name__ == "__main__":

    print("Setup done. Available tables:", TABLES)
    print("\nHow to use (call one table at a time yourself):")
    print("  doc_df   = run_cleaning('doctors')")
    print("  pat_df   = run_cleaning('patients')")
    print("  treat_df = run_cleaning('treatments')")
    print("  appt_df  = run_cleaning('appointments', doctors_df=doc_df)")
    print("  bill_df  = run_cleaning('billing', treatments_df=treat_df)")
    print("\nNote: appointments needs a cleaned doctors_df, billing needs a")
    print("      cleaned treatments_df - pass them in, or run_cleaning() will")
    print("      clean them automatically first if you don't.")
    print("\nRun run_cleaning() for ALL 5 tables before running verification.py")

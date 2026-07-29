# ============================================================
# VERIFICATION.PY
# Flow: read cleaned CSVs -> verify each -> only once ALL 5
#       tables have PASSED, save them into verified/ folder ->
#       build master CSV (join) -> build a subset CSV for
#       visualization/insights.
# All CSVs read/written from the SAME folder as this script,
# except the final verified copies which go into verified/.
# ============================================================

import os
from datetime import datetime
import polars as pl

# ============================================================
# SECTION 1: CONFIG
# ============================================================

# Folder where cleaned CSVs live (output of cleaning.py) and
# where master/subset CSVs will be written. Same folder as this script.
FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(FOLDER, "Output")

# Folder cleaning.py saved the <table>_cleaned.csv files into
CLEANED_DIR = os.path.join(OUTPUT_DIR, "cleaned_data")

# Folder where fully-verified CSVs get copied - ONLY created/filled
# once every single table has passed verification, never before
VERIFIED_FOLDER = os.path.join(OUTPUT_DIR, "verified")

# Folder where master_table.csv and visualization_subset.csv get saved
MASTER_DIR = os.path.join(OUTPUT_DIR, "master_data")
os.makedirs(MASTER_DIR, exist_ok=True)

# Canonical categories every status/payment column should be in after cleaning
VALID_STATUSES = {'Scheduled', 'No-show', 'Cancelled', 'Completed'}
VALID_PAYMENT_STATUSES = {'Paid', 'Pending', 'Failed'}

# Order matters: appointments needs doctors_df, billing needs treatments_df
TABLE_ORDER = ['doctors', 'patients', 'treatments', 'appointments', 'billing']


# ============================================================
# SECTION 2: SMALL HELPERS (csv i/o, printing)
# ============================================================

def csv_path(name):
    return os.path.join(CLEANED_DIR, f"{name}_cleaned.csv")


def load_csv(name):
    path = csv_path(name)
    df = pl.read_csv(path, try_parse_dates=True)
    print(f"Loaded {name}: {df.height} rows from {path}")
    return df


def save_csv(df, filename, folder=MASTER_DIR):
    path = os.path.join(folder, filename)
    df.write_csv(path)
    print(f"Saved: {path} ({df.height} rows, {len(df.columns)} cols)")
    return path


def report(check_name, is_ok, detail=""):
    status = "PASS" if is_ok else "FAIL"
    print(f"[{status}] {check_name}", f"- {detail}" if detail else "")
    return is_ok


def dup_count(df):
    return df.height - df.unique(keep="first").height


# ============================================================
# SECTION 3: VERIFY FUNCTIONS (one per table)
# Each returns True only if ALL checks for that table pass.
# ============================================================

def verify_doctors(df):
    print("\nVerifying: doctors")
    checks = []

    missing_phone = df['phone_number'].null_count()
    checks.append(report("No missing phone_number", missing_phone == 0, f"{missing_phone} missing"))

    missing_exp = df['years_experience'].null_count()
    checks.append(report("years_experience fully numeric", missing_exp == 0, f"{missing_exp} unparseable"))

    bad_branch = df.filter(pl.col('hospital_branch') != pl.col('hospital_branch').str.strip_chars())
    checks.append(report("hospital_branch has no stray whitespace", bad_branch.height == 0, f"{bad_branch.height} bad rows"))

    checks.append(report("No duplicate rows", dup_count(df) == 0))
    return all(checks)


def verify_patients(df):
    print("\nVerifying: patients")
    checks = []

    bad_gender = df.filter(~pl.col('gender').is_in(['Male', 'Female']))
    checks.append(report("Gender values standardized", bad_gender.height == 0, f"{bad_gender.height} bad rows"))

    missing_email = df.filter(pl.col('email') == 'MISSING').height
    missing_address = df.filter(pl.col('address') == 'MISSING').height
    missing_phone = df.filter(pl.col('contact_number') == 'MISSING').height
    checks.append(report("Missing email/address/contact_number all flagged, not blank",
                          df['email'].null_count() == 0 and df['address'].null_count() == 0
                          and df['contact_number'].null_count() == 0,
                          f"flagged as MISSING: email={missing_email}, address={missing_address}, phone={missing_phone}"))

    today = pl.lit(datetime.now().date())
    bad_dob = df.filter(
        pl.col('date_of_birth').is_not_null()
        & ((pl.col('date_of_birth') > today)
           | (((today - pl.col('date_of_birth')).dt.total_days() / 365.25) > 110))
    )
    checks.append(report("No invalid date_of_birth remaining (future / 110+ yrs)", bad_dob.height == 0, f"{bad_dob.height} bad rows"))

    checks.append(report("No duplicate rows", dup_count(df) == 0))
    return all(checks)


def verify_treatments(df):
    print("\nVerifying: treatments")
    checks = []

    negative_cost = df.filter(pl.col('cost') < 0)
    checks.append(report("No negative cost", negative_cost.height == 0, f"{negative_cost.height} rows"))

    missing_cost = df['cost'].null_count()
    checks.append(report("No missing cost", missing_cost == 0, f"{missing_cost} missing"))

    missing_type = df.filter(pl.col('treatment_type') == 'Unknown').height
    checks.append(report("treatment_type has no blanks (filled as 'Unknown')",
                          df['treatment_type'].null_count() == 0, f"filled as Unknown: {missing_type}"))

    checks.append(report("No duplicate rows", dup_count(df) == 0))
    return all(checks)


def verify_appointments(df, doctors_df):
    print("\nVerifying: appointments")
    checks = []

    bad_status = df.filter(~pl.col('status').is_in(list(VALID_STATUSES)))
    checks.append(report("Status values standardized", bad_status.height == 0, f"{bad_status.height} bad rows"))

    known_doctors = set(doctors_df['doctor_id'].drop_nulls().to_list())
    invalid_doctor = df.filter(
        pl.col('doctor_id').is_not_null() & ~pl.col('doctor_id').is_in(known_doctors)
    )
    checks.append(report("Every non-null doctor_id exists in doctors table", invalid_doctor.height == 0, f"{invalid_doctor.height} rows"))

    leftover_na = df.filter(pl.col('reason_for_visit') == 'N/A')
    checks.append(report("No leftover 'N/A' text in reason_for_visit", leftover_na.height == 0, f"{leftover_na.height} rows"))

    checks.append(report("No duplicate rows", dup_count(df) == 0))
    return all(checks)


def verify_billing(df, treatments_df):
    print("\nVerifying: billing")
    checks = []

    bad_status = df.filter(~pl.col('payment_status').is_in(list(VALID_PAYMENT_STATUSES)))
    checks.append(report("payment_status values standardized", bad_status.height == 0, f"{bad_status.height} bad rows"))

    missing_method = df.filter(pl.col('payment_method') == 'MISSING').height
    checks.append(report("payment_method has no blanks (flagged as MISSING)",
                          df['payment_method'].null_count() == 0, f"flagged as MISSING: {missing_method}"))

    merged = df.join(treatments_df.select(['treatment_id', 'cost']), on='treatment_id', how='left')
    mismatch = merged.filter(
        pl.col('cost').is_not_null() & pl.col('amount').is_not_null() & (pl.col('amount') != pl.col('cost'))
    )
    checks.append(report("billing amount matches linked treatment cost", mismatch.height == 0, f"{mismatch.height} mismatches"))

    checks.append(report("No duplicate rows", dup_count(df) == 0))
    return all(checks)


def verify_memory(df, name):
    mem_mb = round(df.estimated_size("mb"), 3)
    print(f"\n{name} memory usage: {mem_mb} MB")


VERIFY_FUNCS = {
    'doctors': verify_doctors,
    'patients': verify_patients,
    'treatments': verify_treatments,
}


# ============================================================
# SECTION: CALL TABLES ONE BY ONE (manual, no auto loop)
# Prints the table name, loads that ONE cleaned CSV, and runs
# its verification checks. A table that FAILS is simply not
# added to VERIFIED_DFS - it does NOT get written anywhere.
# Usage:
#   doc_df   = run_verification('doctors')
#   appt_df  = run_verification('appointments', doctors_df=doc_df)
#   treat_df = run_verification('treatments')
#   bill_df  = run_verification('billing', treatments_df=treat_df)
#   pat_df   = run_verification('patients')
# ============================================================

VERIFIED_DFS = {}  # {table_name: df} — filled only by run_verification() on PASS


def run_verification(table_name, doctors_df=None, treatments_df=None):
    print("\n" + "#" * 70)
    print(f"# TABLE: {table_name}")
    print("#" * 70)

    df = load_csv(table_name)

    if table_name == 'appointments':
        if doctors_df is None:
            doctors_df = load_csv('doctors')
        passed = verify_appointments(df, doctors_df)
    elif table_name == 'billing':
        if treatments_df is None:
            treatments_df = load_csv('treatments')
        passed = verify_billing(df, treatments_df)
    else:
        passed = VERIFY_FUNCS[table_name](df)

    verify_memory(df, table_name)

    if passed:
        # Only tracked in-memory here. It does NOT get saved to the
        # verified/ folder yet - that only happens inside finalize_pipeline(),
        # and only once every table in TABLE_ORDER has passed.
        VERIFIED_DFS[table_name] = df
        print(f"\n✅ '{table_name}' PASSED.")
    else:
        VERIFIED_DFS.pop(table_name, None)
        print(f"\n⚠️  '{table_name}' FAILED verification. It will NOT be saved "
              f"to verified/ until it passes.")

    remaining = [t for t in TABLE_ORDER if t not in VERIFIED_DFS]
    print(f"Verified so far: {len(VERIFIED_DFS)}/{len(TABLE_ORDER)}"
          + (f"  (still need: {remaining})" if remaining else "  — ALL TABLES VERIFIED"))

    return df


# ============================================================
# SECTION 3B: FINALIZE (only runs once ALL 5 tables are verified)
# If even ONE table hasn't passed, this refuses to save anything
# and tells you exactly what's still missing/failed.
# Usage:
#   finalize_pipeline()
# ============================================================

def finalize_pipeline():
    missing = [t for t in TABLE_ORDER if t not in VERIFIED_DFS]

    if missing:
        print("\n⚠️  Cannot proceed — not all tables have passed verification yet.")
        print(f"Still missing / failed: {missing}")
        print("Fix the ones above in cleaning.py, re-run run_verification() for them, then try again.")
        return

    print("\n" + "=" * 60)
    print("All 5 tables verified — saving to verified/, building master + subset")
    print("=" * 60)

    # ---- Step 1: save every verified table into verified/ (only now) ----
    os.makedirs(VERIFIED_FOLDER, exist_ok=True)
    for name, df in VERIFIED_DFS.items():
        save_csv(df, f"{name}.csv", folder=VERIFIED_FOLDER)

    # ---- Step 2: build + save master CSV (all 5 tables joined) ----
    master_df = build_master_table(VERIFIED_DFS)
    master_path = save_csv(master_df, "master_table.csv")

    # ---- Step 3: re-read master CSV from disk, build the subset from it ----
    master_from_disk = pl.read_csv(master_path, try_parse_dates=True)
    subset_df = build_visualization_subset(master_from_disk)
    save_csv(subset_df, "visualization_subset.csv")

    print("\n✅ Pipeline complete: verified -> saved to verified/ -> master CSV -> subset CSV")


# ============================================================
# SECTION 4: MASTER CSV BUILDER (joins all 5 tables)
# appointments -> patients -> doctors -> treatments -> billing
# ============================================================

def build_master_table(dfs):
    print("\n" + "=" * 60)
    print("Building master table (all 5 tables joined)")
    print("=" * 60)

    appt = dfs['appointments']
    pat = dfs['patients'].with_columns(
        (pl.col('first_name') + ' ' + pl.col('last_name')).alias('patient_name')
    )
    doc = dfs['doctors'].with_columns(
        (pl.col('first_name') + ' ' + pl.col('last_name')).alias('doctor_name')
    )
    treat = dfs['treatments']
    bill = dfs['billing']

    df = appt.join(
        pat.select(['patient_id', 'patient_name', 'gender', 'date_of_birth', 'insurance_provider']),
        on='patient_id', how='left'
    )
    df = df.join(
        doc.select(['doctor_id', 'doctor_name', 'specialization', 'hospital_branch']),
        on='doctor_id', how='left'
    )
    df = df.join(
        treat.select(['appointment_id', 'treatment_id', 'treatment_type', 'description',
                       'cost', 'treatment_date']),
        on='appointment_id', how='left'
    )
    df = df.join(
        bill.select(['treatment_id', 'amount', 'payment_method', 'payment_status', 'bill_date']),
        on='treatment_id', how='left'
    )

    print(f"Master table built: {df.height} rows, {len(df.columns)} columns")
    return df


# ============================================================
# SECTION 5: VISUALIZATION SUBSET BUILDER
# Reads the master CSV that was actually saved to disk, and
# keeps only the columns needed for the 5th project's charts
# (Polars + Plotly / Plotly Express).
# ============================================================

def build_visualization_subset(master_df):
    subset_cols = [
        'appointment_id', 'patient_id', 'patient_name', 'gender', 'date_of_birth',
        'doctor_id', 'doctor_name', 'specialization', 'hospital_branch',
        'appointment_date', 'appointment_time', 'status',
        'treatment_type', 'description', 'cost', 'treatment_date',
        'amount', 'payment_method', 'payment_status', 'bill_date',
    ]
    available = [c for c in subset_cols if c in master_df.columns]
    return master_df.select(available)


# ============================================================
# Run: python -i verification.py
# Then call run_verification('table_name') for each of the 5
# tables yourself. Only once ALL 5 have PASSED, call
# finalize_pipeline() to save to verified/ + build master + subset.
# ============================================================
if __name__ == "__main__":
    print("Setup done. Tables to verify:", TABLE_ORDER)
    print("\nHow to use (call one table at a time yourself):")
    print("  doc_df   = run_verification('doctors')")
    print("  pat_df   = run_verification('patients')")
    print("  treat_df = run_verification('treatments')")
    print("  appt_df  = run_verification('appointments', doctors_df=doc_df)")
    print("  bill_df  = run_verification('billing', treatments_df=treat_df)")
    print("\nOnce all 5 have PASSED:")
    print("  finalize_pipeline()   # saves to verified/, builds master_table.csv + visualization_subset.csv")

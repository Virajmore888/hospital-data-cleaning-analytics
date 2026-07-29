<div align="center">

# 🏥 Healthcare Analytics: Messy Data Cleaning & Insights Pipeline

### *200 appointments. 5 linked hospital tables. 8 answered business questions, no database required.*

---

<!-- Tech Stack -->
![Python](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12%20|%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-0.20+-CD792C?style=for-the-badge&logo=polars&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.21+-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.4+-11557c?style=for-the-badge&logo=python&logoColor=white)
![Seaborn](https://img.shields.io/badge/Seaborn-0.11+-4c72b0?style=for-the-badge&logo=python&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.0+-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)

<!-- Links -->
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Viraj%20More-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/viraj-uttam-more-a24a80391)
[![Email](https://img.shields.io/badge/Email-Contact%20Me-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:virajmore.data888@gmail.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](./LICENSE)

---

**[📝 Full Report](docs/) · [💻 Raw Data](data/) · [📦 Output](Output/) · [🐍 Python Code](python/) · [📦 Requirements](requirements.txt) · [🤝 Contributing](CONTRIBUTING.md)**

</div>

---

## 👋 About This Project

This is an **end to end healthcare analytics pipeline** built entirely on **Python and Polars**, going from a raw, deliberately messy dataset all the way to a written report and interactive charts, with no database required.

Hospital operations generate data across many disconnected systems: patient records, doctor schedules, treatments, appointments, and billing. In the real world, this data rarely arrives clean. Dates are formatted five different ways, records go missing, billing amounts do not match up with treatments, and no-shows quietly cost hospitals revenue every single day.

This project starts from a dataset built specifically to simulate that reality. Rather than a casually generated sample, the data was deliberately engineered to reproduce the kinds of inconsistencies real hospital systems produce, mixed date formats, duplicate and missing records, and billing mismatches, so the cleaning pipeline actually has real problems to solve rather than a dataset that is clean by default.

The pipeline explores the raw CSVs, cleans and standardizes each of the 5 tables, verifies the cleaned output, joins everything into a master table, and answers concrete operational questions with interactive Plotly charts and a written insights report.

> If you are a recruiter or fellow analyst, the TL;DR below tells you everything in 30 seconds. The rest of the README is for anyone who wants the full pipeline detail.

---

## ⚡ TL;DR - Key Findings

| # | Finding | Business Impact |
|---|---------|----------------|
| 1 | 🚫 **26.00% overall no-show rate** across 200 appointments | Roughly 1 in 4 booked appointments is a no-show, a major scheduling and revenue leak |
| 2 | 🩺 **Dermatology has the highest no-show rate** at 27.94% | Reminder systems or overbooking strategies should be targeted at this specialization first |
| 3 | 💳 **Failed payments average 2,863.76** vs **2,676.79** for paid/pending | Costlier treatments are harder to collect on, a collections risk worth flagging early |
| 4 | 👥 **Male patients no-show more often** (26.92%) than female patients (24.29%) | A modest but real gap worth factoring into reminder targeting |
| 5 | 🏥 **Central Hospital generates the most revenue** at 195,862.74 | Clear branch-level performance signal for resource allocation |
| 6 | 📊 **Patient age has almost no link to treatment cost** (correlation 0.07) | Cost drivers lie elsewhere, likely treatment type, not patient demographics |

---

## 🎯 What Makes This Project Different

Most healthcare analytics projects work off a single pre-cleaned CSV. This one starts from data engineered to be genuinely messy.

| Typical Healthcare Project | This Project |
|---|---|
| Starts from one flat, already-clean CSV | Starts from 5 raw tables with realistic messiness built in on purpose |
| Cleans one dataset | Cleans and verifies 5 tables independently before joining |
| Shows a single summary stat | Answers 8 specific operational questions with numpy-backed statistics |
| Static charts only | 5 interactive Plotly charts, including a specialization/doctor/treatment sunburst |
| Notebook with mixed logic | Modular pipeline: EDA, clean, verify, visualize, and report as separate scripts |
| Needs a database | Runs entirely off local CSVs, no database setup required |

---

## 💡 Key Business Insights

### 1. 🚫 Overall No-Show Rate

Out of 200 appointments, **26.00% ended up as a no-show**. This is the headline operational metric, roughly a quarter of scheduled appointments never happen, directly affecting doctor utilization and hospital revenue.

---

### 2. 🩺 No-Show Rate by Specialization

**Dermatology has the highest no-show rate at 27.94%**, above the hospital-wide average. This points to a specialization-specific scheduling or reminder gap worth investigating further.

---

### 3. 💰 Cost Gap Between Paid and Pending Treatments

Pending treatments cost **51.25 less on average** than paid ones (paid mean 2,703.63 vs pending mean 2,652.39). The gap is small, suggesting payment status is not strongly tied to treatment cost on its own.

---

### 4. 🧾 Average Treatment Cost

The overall average treatment cost is **2,738.91**, with unrecorded/unknown treatment types averaging the highest cost at **3,507.37**, a data quality gap worth cleaning up at the source.

---

### 5. 👥 No-Show Rate by Gender

Male patients no-show at **26.92%**, compared to **24.29%** for female patients. The gap is modest but consistent enough to factor into reminder call targeting.

---

### 6. 📈 Patient Age vs Treatment Cost

The correlation between patient age and treatment cost is **0.07**, essentially no meaningful link. Treatment cost is driven by what is being treated, not how old the patient is.

---

### 7. 🏥 Revenue by Hospital Branch

**Central Hospital generates the highest revenue** at **195,862.74**, a clear signal for where operational and staffing investment is paying off most.

---

### 8. 💳 Failed Payments and Treatment Cost

Failed payments average **2,863.76**, higher than the **2,676.79** average for paid or pending payments. Costlier treatments appear harder to collect on, larger bills may need more active follow-up.

---

## 📋 Key Metrics At A Glance

| Metric | Value |
|--------|-------|
| **Total Appointment Records** | 200 |
| **Overall No-Show Rate** | 26.00% |
| **Highest No-Show Specialization** | Dermatology (27.94%) |
| **Average Treatment Cost** | 2,738.91 |
| **Most Expensive Treatment Category** | Unknown/unrecorded (3,507.37) |
| **Male No-Show Rate** | 26.92% |
| **Female No-Show Rate** | 24.29% |
| **Top Revenue Branch** | Central Hospital (195,862.74) |
| **Age vs Cost Correlation** | 0.07 (no meaningful link) |
| **Linked Tables** | 5 (doctors, patients, treatments, appointments, billing) |

---

## ⚙️ Technical Architecture

Built as a fully relational-style pipeline over local CSVs, so the project mirrors how hospital data is structured in real systems without requiring a database.

| Technique | Implementation Detail |
|---|---|
| **Multi-Table Design** | 5 linked CSV tables (doctors, patients, treatments, appointments, billing) joined by ID |
| **Data Cleaning** | Mixed date formats standardized, duplicates and invalid records handled per table via `cleaning.py` |
| **Verification Layer** | Cleaned tables re-checked and only promoted to `verified/` once every table passes, via `verification.py` |
| **Master Table Construction** | All 5 tables joined into a single master table, with a trimmed subset built for downstream analysis |
| **Exploratory Data Analysis** | Per-table categorical and numeric distribution plots via `EDA.py` |
| **Business Insight Generation** | 8 healthcare questions answered with `numpy` in `insights.py`, printed and saved as a text report |
| **Visualization** | 5 interactive charts, including a sunburst breakdown, built with `Plotly` in `visualization.py` |

---

## 🛠️ Skills Demonstrated

`Python` · `Polars` · `NumPy` · `Matplotlib` · `Seaborn` · `Plotly` · `Data Cleaning` · `Data Verification` · `Exploratory Data Analysis` · `Business Intelligence` · `Interactive Data Visualization`

---

## 🚀 Run This Project Locally

### Prerequisites
- Python 3.10 to 3.13
- pip

### Step 1: Clone
```bash
git clone https://github.com/Virajmore888/hospital-data-cleaning-analytics.git
cd hospital-data-cleaning-analytics
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Pipeline
```bash
python EDA.py             # exploratory plots -> Output/eda_plots/
python cleaning.py        # cleans raw tables -> Output/cleaned_data/
python verification.py    # verifies data, builds master table -> Output/verified/, Output/master_data/
python visualization.py   # interactive charts -> Output/charts/
python insights.py        # insights report -> Output/reports/
```

No database or `.env` file is needed, everything runs off the CSVs in `data/`.

---

## 📦 Dependencies

📄 [View requirements.txt](https://github.com/Virajmore888/hospital-data-cleaning-analytics/blob/a34422d84658c0943672ba4b98a48b12ef8b58f5/requirements.txt)

```
polars
numpy
matplotlib
seaborn
plotly
```

---

## 📊 Dataset At A Glance

| Attribute | Value |
|---|---|
| **Source** | Custom-built dataset engineered to reproduce real-world hospital data issues, not a casually generated sample |
| **Total Appointment Records** | 200 |
| **Linked Tables** | 5 (doctors, patients, treatments, appointments, billing) |
| **Doctor Records** | 10 |
| **Patient Records** | 53 |
| **Treatment Records** | 200 |
| **Billing Records** | 203 |
| **Master Table Columns** | 23 (after joining all 5 tables) |

---

## 📂 Repository Structure

```
hospital-data-cleaning-analytics/
|
+-- data/
|   +-- doctors.csv                    # Raw doctor records (specialization, branch, experience)
|   +-- patients.csv                   # Raw patient records (demographics, insurance)
|   +-- treatments.csv                 # Raw treatment records linked to appointments
|   +-- appointments.csv               # Raw appointment records linked to patients & doctors
|   +-- billing.csv                    # Raw billing records linked to treatments
|
+-- python/
|   +-- EDA.py                         # Exploratory data analysis and plots
|   +-- cleaning.py                    # Cleans each raw table
|   +-- verification.py                # Verifies cleaned data, builds master table
|   +-- visualization.py               # 5 interactive Plotly charts
|   +-- insights.py                    # 8 healthcare questions answered, saved as report
|
+-- Output/
|   +-- cleaned_data/                  # 5 cleaned CSVs
|   +-- verified/                      # Final verified CSVs
|   +-- master_data/                   # master_table.csv plus visualization subset
|   +-- eda_plots/                     # Per-table exploratory plots
|   +-- charts/                        # 5 interactive HTML charts
|   +-- reports/                       # insights_report.txt
|
+-- docs/
|   +-- Healthcare_Analysis_Report.pdf         # Full written report
|   +-- Healthcare_Analysis_Presentation.pdf   # Stakeholder-ready slide deck
|
+-- requirements.txt
+-- CONTRIBUTING.md
+-- .gitignore
+-- README.md
```

---

## 🤝 Connect & Contribute

- 🔗 **LinkedIn:** [Viraj More](https://www.linkedin.com/in/viraj-uttam-more-a24a80391)
- 📧 **Email:** [virajmore.data888@gmail.com](mailto:virajmore.data888@gmail.com)
- 💻 **GitHub:** [hospital-data-cleaning-analytics](https://github.com/Virajmore888/hospital-data-cleaning-analytics)

Found something to improve? Open an **Issue** or submit a **Pull Request**, contributions are welcome.
Read the **[Contributing Guide](https://github.com/Virajmore888/hospital-data-cleaning-analytics/blob/a34422d84658c0943672ba4b98a48b12ef8b58f5/CONTRIBUTING.md)** before submitting.

---

## 📄 License

MIT License, see [LICENSE](./LICENSE) for details.

---

<div align="center">

**Built end to end with Python and Polars**

*If this project added value, consider leaving a ⭐ on the repo, it helps others find it too.*

</div>

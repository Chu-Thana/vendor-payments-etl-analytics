# Superstore ETL & Analytics Project

## Overview
This project demonstrates an end-to-end analytics pipeline, from raw data ingestion and validation to analytics-ready data modeling and business intelligence visualization.

Rather than focusing solely on dashboards, this project emphasizes **data quality, reliability, and explainability**, reflecting real-world analytics and analytics engineering practices.

---

## Problem Statement
In real-world analytics, data may appear “clean” on the surface while still containing hidden inconsistencies that can break downstream analysis.

This project simulates a production-like analytics workflow that:
- Validates incoming data before analysis
- Detects anomalies and logical inconsistencies
- Produces analytics-ready tables for reliable BI consumption

---

## Architecture
Raw Data  
→ **Python ETL** (Validation & Cleaning)  
→ **SQL** (Star Schema & Analytics Views)  
→ **Power BI** (Business Insights)

---

## Tech Stack
- **Python**: Pandas, NumPy (ETL, validation, data quality checks)
- **SQL (SQLite)**: Star-schema-style modeling, analytics views
- **Power BI**: Business dashboards and insight exploration
- **GitHub**: Version control and project documentation

---

## Project Structure
```text
superstore-etl-analytics/
├─ Data/        # Raw Superstore dataset
├─ ETL/         # Python ETL pipeline
├─ SQL/         # SQL views and example analytics queries
├─ PowerBI/     # Power BI dashboard
└─ README.md
```

---

## Data Pipeline Steps
- Raw data ingestion
- Data validation and anomaly detection
- Data cleaning and transformation
- Star schema modeling (fact and dimension tables)
- Analytics-ready SQL views
- Business visualization in Power BI

---

## Key Features
- Data validation before analytics
- Explicit handling of edge cases and anomalies
- Analytics-ready schema design
- Clear separation between ETL, modeling, and visualization layers
- Reproducible and auditable workflow

---

## Outputs
- Cleaned datasets
- Fact and dimension-style tables
- Analytics SQL views
- Power BI dashboard (4 pages):
  - Sales & profit trends
  - Regional and category performance
  - Discount vs profit analysis
  - High-discount dependency risk

---

## How to Run
1. Clone this repository
2. Run the Python ETL scripts in the `ETL/` folder
3. Execute SQL scripts in the `SQL/` folder to create analytics views
4. Open the Power BI file in the `PowerBI/` folder to explore insights

---

## Notes
This project prioritizes **system design, data reliability, and analytical correctness** over purely visual complexity, aligning with real-world analytics engineering and data analyst workflows.

---




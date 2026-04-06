# 📊 Superstore ETL & Analytics Pipeline

![Python](https://img.shields.io/badge/Python-3.12-blue)
![ETL](https://img.shields.io/badge/Pipeline-ETL-orange)
![Pandas](https://img.shields.io/badge/Processing-Pandas-lightblue)
![SQL](https://img.shields.io/badge/Analytics-SQL-lightgrey)
![Modeling](https://img.shields.io/badge/Model-Star%20Schema-green)
![Logging](https://img.shields.io/badge/Logs-Structured-brightgreen)

A production-style batch data pipeline that transforms raw transactional data into analytics-ready datasets using validation, structured transformation, and dimensional modeling.

---

# 🧠 Design Goals

This project simulates a **production-style batch ETL pipeline** commonly used in modern analytics platforms.

Key objectives:

- Validate incoming raw data before processing
- Detect anomalies and logical inconsistencies
- Apply structured transformation logic
- Build a star schema for analytical workloads
- Ensure data quality and reproducibility
- Produce analytics-ready datasets for BI systems

---

# 🚀 Tech Stack

- Python 3.12
- Pandas
- SQLite
- SQL (Analytical Queries)
- Structured Logging
- CSV Data Sources
- Git
- Power BI (Dashboard & Visualization)

---

# 📂 Project Structure

```text
superstore-etl-analytics/

├── data/                        # Raw input data (CSV)
├── output/                      # Cleaned data, reports, database
├── SQL/                         # Analytical queries / views
├── clean_superstore.py          # Data cleaning logic
├── superstore_analytics.pbix    # Power BI dashboard
├── Superstore.csv               # Raw dataset
└── main.py                      # Pipeline entrypoint (optional)
```

---

# 🏗 Architecture Overview

```mermaid
flowchart LR

Raw["Raw CSV Data"]
Validate["Data Validation"]
Transform["Transformation Layer (Pandas)"]
Model["Data Modeling (Fact + Dimensions)"]
Views["SQL Analytical Views"]
BI["BI / Dashboard"]

Raw --> Validate
Validate --> Transform
Transform --> Model
Model --> Views
Views --> BI
```

## 📊 Analytics Layer

This project includes a Power BI dashboard built on top of the processed data.

Key features:
- Sales performance analysis by region, category, and segment
- Time-based trends (monthly / yearly sales)
- Top-performing products and regions
- Interactive filtering for deeper analysis

The dashboard connects to the transformed data stored in SQLite and provides business insights for decision-making.
This layer demonstrates how raw data is transformed into actionable insights through analytical modeling and visualization.

---

# 🔄 Data Flow

### 1️⃣ Raw Data Ingestion
- Load raw transactional dataset (CSV)
- Initial schema inspection

### 2️⃣ Data Validation
- Null checks
- Data type enforcement
- Logical consistency validation

### 3️⃣ Transformation Layer
- Data cleaning and normalization
- Feature engineering
- Derived metrics calculation

### 4️⃣ Data Modeling
Builds a **star schema**:
- Fact table: sales transactions
- Dimension tables: customer, product, region

### 5️⃣ Analytics Layer
- SQL-based analytical views
- Pre-aggregated datasets for BI queries

### 📷 Dashboard Preview

![Dashboard](assets/dashboard_preview.png)
📁 File: superstore_analytics.pbix
---

# 📊 Output

- Cleaned datasets
- Fact and dimension tables
- SQL views for reporting

---

# 🐍 Running the Pipeline

```bash
python main.py
```

---

# 📊 Observability

- Structured logging
- ETL execution logs

---

# 📐 Key Design Decisions

- Layered architecture (Validation → Transform → Model)
- Star schema for analytical performance
- Pandas for transformation
- SQL for analytics layer

---

# 🎯 Batch Processing Characteristics

- Deterministic processing
- Data quality first
- Layered pipeline design

---

# 🔮 Future Improvements

- Airflow orchestration
- PostgreSQL / Data Warehouse
- Data quality monitoring
- FastAPI integration

---

# 🏁 Portfolio Context

```text
Batch ETL (this project)
      ↓
Analytics API
      ↓
Streaming Pipeline
      ↓
Orchestration (Airflow)
```

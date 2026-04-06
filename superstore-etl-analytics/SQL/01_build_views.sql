-- 01_build_views.sql
-- Purpose : Build analytics-ready views and indexes for Superstore ETL project (SQLite)
-- Focus   : Sales performance + Region performance (AE/DE-style: views + performance + data auditability)
-- Author  : Thana
-- Database: superstore.db
--
-- Tables produced by Python ETL:
--   - superstore_clean      (cleaned fact table + quality flags)
--   - superstore_rejected   (rows rejected by validation rules)
--   - etl_run_log           (ETL run metadata)
--
-- How to run:
--   1) Open superstore.db in DB Browser for SQLite / DBeaver / VS Code SQLite extension
--   2) Execute this file top-to-bottom AFTER Python ETL completes
--   3) Safe to rerun: uses DROP VIEW IF EXISTS + CREATE INDEX IF NOT EXISTS
--
-- Notes:
--   - CREATE INDEX writes to the DB file. If DB is read-only/locked, skip the Index section.
--   - Date grouping uses STRFTIME with DATE(...) to avoid timestamp issues.
-- =====================================================================


/* ---------------------------------------------------------------------
   1) Performance indexes (safe to re-run)
   Skip if DB is read-only or locked.
------------------------------------------------------------------------ */
CREATE INDEX IF NOT EXISTS idx_sc_order_date    ON superstore_clean(order_date);
CREATE INDEX IF NOT EXISTS idx_sc_ship_date     ON superstore_clean(ship_date);
CREATE INDEX IF NOT EXISTS idx_sc_customer_id   ON superstore_clean(customer_id);
CREATE INDEX IF NOT EXISTS idx_sc_product_id    ON superstore_clean(product_id);
CREATE INDEX IF NOT EXISTS idx_sc_region        ON superstore_clean(region);
CREATE INDEX IF NOT EXISTS idx_sc_category      ON superstore_clean(category);
CREATE INDEX IF NOT EXISTS idx_sc_sub_category  ON superstore_clean(sub_category);
CREATE INDEX IF NOT EXISTS idx_sc_state         ON superstore_clean(state);

-- Composite indexes for common analytic slices (AE-ish polish)
CREATE INDEX IF NOT EXISTS idx_sc_orderdate_region
ON superstore_clean(order_date, region);

CREATE INDEX IF NOT EXISTS idx_sc_category_subcat
ON superstore_clean(category, sub_category);


/* ---------------------------------------------------------------------
   2) Core reusable view: v_superstore_orders
   Adds reusable date fields + ship_days (useful in PBI without DAX).
------------------------------------------------------------------------ */
DROP VIEW IF EXISTS v_superstore_orders;
CREATE VIEW v_superstore_orders AS
SELECT
  row_id,
  order_id,

  order_date,
  ship_date,
  ship_mode,

  customer_id,
  customer_name,
  segment,

  country,
  city,
  state,
  postal_code,
  region,

  product_id,
  category,
  sub_category,
  product_name,

  sales,
  quantity,
  discount,
  profit,

  flag_negative_profit,
  flag_high_discount,

  -- Reusable date fields (timestamp-safe)
  DATE(order_date)                         AS order_day,
  STRFTIME('%Y-%m', DATE(order_date))      AS order_month,
  CAST(STRFTIME('%Y', DATE(order_date)) AS INT) AS order_year,

  DATE(ship_date)                          AS ship_day,
  STRFTIME('%Y-%m', DATE(ship_date))       AS ship_month,

  -- Shipping lead time in days (integer)
  CAST(
    julianday(DATE(ship_date)) - julianday(DATE(order_date))
    AS INT
  ) AS ship_days

FROM superstore_clean;


/* ---------------------------------------------------------------------
   3) Minimal dims (Star-schema ready)
   Optional but recommended for AE/DE portfolio.
------------------------------------------------------------------------ */
DROP VIEW IF EXISTS dim_customer;
CREATE VIEW dim_customer AS
SELECT
  customer_id,
  MAX(customer_name) AS customer_name,
  MAX(segment)       AS segment,
  MAX(region)        AS region,
  MAX(state)         AS state,
  MAX(city)          AS city,
  MAX(country)       AS country
FROM v_superstore_orders
GROUP BY customer_id;

DROP VIEW IF EXISTS dim_product;
CREATE VIEW dim_product AS
SELECT
  product_id,
  MAX(product_name)  AS product_name,
  MAX(category)      AS category,
  MAX(sub_category)  AS sub_category
FROM v_superstore_orders
GROUP BY product_id;

-- Month grain date dimension for PBI relationships (simple but effective)
DROP VIEW IF EXISTS dim_date_month;
CREATE VIEW dim_date_month AS
WITH bounds AS (
  SELECT
    date(MIN(order_month || '-01')) AS min_month,
    date(MAX(order_month || '-01')) AS max_month
  FROM v_superstore_orders
),
calendar AS (
  SELECT min_month AS month_start FROM bounds
  UNION ALL
  SELECT date(month_start, '+1 month')
  FROM calendar, bounds
  WHERE month_start < max_month
)
SELECT
  strftime('%Y-%m', month_start) AS order_month,
  month_start
FROM calendar;

/* ---------------------------------------------------------------------
   4) KPI Views for Power BI (Sales performance)
------------------------------------------------------------------------ */

-- 4.1 Overall KPI (single-row table)
DROP VIEW IF EXISTS v_kpi_overall;
CREATE VIEW v_kpi_overall AS
SELECT
  COUNT(*)                         AS rows_cnt,
  COUNT(DISTINCT order_id)         AS orders_cnt,
  COUNT(DISTINCT customer_id)      AS customers_cnt,
  COUNT(DISTINCT product_id)       AS products_cnt,
  SUM(sales)                       AS total_sales,
  SUM(profit)                      AS total_profit,
  ROUND(AVG(discount), 4)          AS avg_discount,
  ROUND(AVG(ship_days), 2)         AS avg_ship_days
FROM v_superstore_orders;

-- 4.2 Sales & Profit by Month (core chart)
DROP VIEW IF EXISTS v_sales_profit_by_month;
CREATE VIEW v_sales_profit_by_month AS
SELECT
  order_month,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(*)    AS rows_cnt,
  COUNT(DISTINCT order_id) AS orders_cnt,
  ROUND(AVG(discount), 4)  AS avg_discount
FROM v_superstore_orders
GROUP BY order_month
ORDER BY order_month;

-- 4.3 Month-over-Month growth (window functions)
DROP VIEW IF EXISTS v_sales_profit_mom;
CREATE VIEW v_sales_profit_mom AS
WITH m AS (
  SELECT
    order_month,
    SUM(sales)  AS total_sales,
    SUM(profit) AS total_profit
  FROM v_superstore_orders
  GROUP BY order_month
)
SELECT
  order_month,
  total_sales,
  total_profit,

  LAG(total_sales)  OVER (ORDER BY order_month) AS prev_sales,
  LAG(total_profit) OVER (ORDER BY order_month) AS prev_profit,

  (total_sales  - LAG(total_sales)  OVER (ORDER BY order_month)) AS sales_delta,
  (total_profit - LAG(total_profit) OVER (ORDER BY order_month)) AS profit_delta,

  ROUND(
    100.0 * (total_sales - LAG(total_sales) OVER (ORDER BY order_month))
    / NULLIF(LAG(total_sales) OVER (ORDER BY order_month), 0),
    2
  ) AS sales_mom_pct,

  ROUND(
    100.0 * (total_profit - LAG(total_profit) OVER (ORDER BY order_month))
    / NULLIF(LAG(total_profit) OVER (ORDER BY order_month), 0),
    2
  ) AS profit_mom_pct
FROM m
ORDER BY order_month;

-- 4.4 Category performance
DROP VIEW IF EXISTS v_category_performance;
CREATE VIEW v_category_performance AS
SELECT
  category,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(*)    AS rows_cnt,
  COUNT(DISTINCT order_id) AS orders_cnt,
  ROUND(AVG(discount), 4)  AS avg_discount
FROM v_superstore_orders
GROUP BY category
ORDER BY total_profit DESC;

-- 4.5 Sub-category profitability (identify winners/losers)
DROP VIEW IF EXISTS v_subcategory_performance;
CREATE VIEW v_subcategory_performance AS
SELECT
  category,
  sub_category,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(*)    AS rows_cnt,
  ROUND(AVG(discount), 4)  AS avg_discount,
  ROUND(1.0 * SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin
FROM v_superstore_orders
GROUP BY category, sub_category
ORDER BY total_profit DESC;

-- 4.6 Top customers by sales/profit (for ranking visuals)
DROP VIEW IF EXISTS v_top_customers;
CREATE VIEW v_top_customers AS
SELECT
  customer_id,
  customer_name,
  segment,
  region,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(DISTINCT order_id) AS orders_cnt
FROM v_superstore_orders
GROUP BY customer_id, customer_name, segment, region
ORDER BY total_sales DESC;


/* ---------------------------------------------------------------------
   5) Region Performance Views
------------------------------------------------------------------------ */

-- 5.1 Region summary (core)
DROP VIEW IF EXISTS v_region_performance;
CREATE VIEW v_region_performance AS
SELECT
  region,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(*)    AS rows_cnt,
  COUNT(DISTINCT order_id) AS orders_cnt,
  ROUND(AVG(discount), 4) AS avg_discount,
  ROUND(AVG(ship_days), 2) AS avg_ship_days,
  ROUND(1.0 * SUM(profit) / NULLIF(SUM(sales), 0), 4) AS profit_margin
FROM v_superstore_orders
GROUP BY region
ORDER BY total_profit DESC;

-- 5.2 Region × Month (trend lines / small multiples)
DROP VIEW IF EXISTS v_region_monthly;
CREATE VIEW v_region_monthly AS
SELECT
  order_month,
  region,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit,
  COUNT(DISTINCT order_id) AS orders_cnt,
  ROUND(AVG(discount), 4) AS avg_discount
FROM v_superstore_orders
GROUP BY order_month, region
ORDER BY order_month, region;

-- 5.3 Region MoM (window by region)
DROP VIEW IF EXISTS v_region_mom;
CREATE VIEW v_region_mom AS
WITH rm AS (
  SELECT
    order_month,
    region,
    SUM(sales)  AS total_sales,
    SUM(profit) AS total_profit
  FROM v_superstore_orders
  GROUP BY order_month, region
)
SELECT
  order_month,
  region,
  total_sales,
  total_profit,
  LAG(total_sales) OVER (PARTITION BY region ORDER BY order_month) AS prev_sales,
  LAG(total_profit) OVER (PARTITION BY region ORDER BY order_month) AS prev_profit,

  ROUND(
    100.0 * (total_sales - LAG(total_sales) OVER (PARTITION BY region ORDER BY order_month))
    / NULLIF(LAG(total_sales) OVER (PARTITION BY region ORDER BY order_month), 0),
    2
  ) AS sales_mom_pct,

  ROUND(
    100.0 * (total_profit - LAG(total_profit) OVER (PARTITION BY region ORDER BY order_month))
    / NULLIF(LAG(total_profit) OVER (PARTITION BY region ORDER BY order_month), 0),
    2
  ) AS profit_mom_pct
FROM rm
ORDER BY region, order_month;


/* ---------------------------------------------------------------------
   6) Data Quality / Audit Views (tie to ETL flags)
------------------------------------------------------------------------ */

-- 6.1 Flag rates by month (trend)
DROP VIEW IF EXISTS v_quality_flags_by_month;
CREATE VIEW v_quality_flags_by_month AS
SELECT
  order_month,
  COUNT(*) AS total_rows,
  SUM(flag_negative_profit) AS negative_profit_rows,
  SUM(flag_high_discount)   AS high_discount_rows,
  ROUND(100.0 * SUM(flag_negative_profit) / COUNT(*), 2) AS pct_negative_profit,
  ROUND(100.0 * SUM(flag_high_discount)   / COUNT(*), 2) AS pct_high_discount
FROM v_superstore_orders
GROUP BY order_month
ORDER BY order_month;

-- 6.2 High discount concentration by sub-category
DROP VIEW IF EXISTS v_quality_high_discount_subcat;
CREATE VIEW v_quality_high_discount_subcat AS
SELECT
  sub_category,
  COUNT(*) AS total_rows,
  SUM(flag_high_discount) AS high_discount_rows,
  ROUND(100.0 * SUM(flag_high_discount) / COUNT(*), 2) AS pct_high_discount,
  ROUND(AVG(discount), 4) AS avg_discount,
  SUM(sales)  AS total_sales,
  SUM(profit) AS total_profit
FROM v_superstore_orders
GROUP BY sub_category
HAVING SUM(flag_high_discount) > 0
ORDER BY high_discount_rows DESC, pct_high_discount DESC;

-- 6.3 Negative profit hotspots by sub-category
DROP VIEW IF EXISTS v_quality_negative_profit_subcat;
CREATE VIEW v_quality_negative_profit_subcat AS
SELECT
  sub_category,
  COUNT(*) AS total_rows,
  SUM(flag_negative_profit) AS negative_profit_rows,
  ROUND(100.0 * SUM(flag_negative_profit) / COUNT(*), 2) AS pct_negative_profit,
  SUM(profit) AS total_profit
FROM v_superstore_orders
GROUP BY sub_category
HAVING SUM(flag_negative_profit) > 0
ORDER BY negative_profit_rows DESC, pct_negative_profit DESC;


-- 6.4 Data Quality / Audit Views
DROP VIEW IF EXISTS dq_customer_location_conflict;
CREATE VIEW dq_customer_location_conflict AS
SELECT
  customer_id,
  COUNT(DISTINCT region) AS region_variants,
  COUNT(DISTINCT state)  AS state_variants,
  COUNT(DISTINCT city)   AS city_variants
FROM v_superstore_orders
GROUP BY customer_id
HAVING region_variants > 1
    OR state_variants  > 1
    OR city_variants   > 1
ORDER BY city_variants DESC, state_variants DESC, region_variants DESC;



/* ---------------------------------------------------------------------
   7) ETL monitoring views (operational credibility)
------------------------------------------------------------------------ */

-- Last run summary (single row)
DROP VIEW IF EXISTS v_etl_last_run;
CREATE VIEW v_etl_last_run AS
SELECT
  run_id,
  run_at,
  source_file,
  rows_before,
  rows_after,
  dropped_rows
FROM etl_run_log
ORDER BY run_at DESC
LIMIT 1;

-- Run history (for a PBI "Pipeline Health" page)
DROP VIEW IF EXISTS v_etl_run_history;
CREATE VIEW v_etl_run_history AS
SELECT
  run_at,
  source_file,
  rows_before,
  rows_after,
  dropped_rows,
  ROUND(100.0 * dropped_rows / NULLIF(rows_before, 0), 2) AS drop_rate_pct
FROM etl_run_log
ORDER BY run_at DESC;

-- End of 01_build_views.sql

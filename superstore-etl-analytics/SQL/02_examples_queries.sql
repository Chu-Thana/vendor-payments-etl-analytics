-- 02_examples_queries.sql
-- Purpose : Example analytical queries using analytics-ready views (SQLite)
-- Focus   : Sales performance + Region performance (portfolio / interview-friendly)
-- Author  : Thana
--
-- IMPORTANT:
--   This file does NOT modify the database schema.
--   It contains SELECT-only queries and is safe to run anytime.
--
-- Pre-req:
--   Run 01_build_views.sql first (to create the views).
-- =====================================================================

/* ---------------------------------------------------------------------
   A) Sanity checks (tables + date range)
------------------------------------------------------------------------ */
SELECT 'rows_superstore_clean'    AS metric, COUNT(*) AS value FROM superstore_clean;
SELECT 'rows_superstore_rejected' AS metric, COUNT(*) AS value FROM superstore_rejected;
SELECT 'etl_runs'                 AS metric, COUNT(*) AS value FROM etl_run_log;

SELECT
  MIN(DATE(order_date)) AS min_order_date,
  MAX(DATE(order_date)) AS max_order_date
FROM superstore_clean;

SELECT
  run_at,
  source_file,
  rows_before,
  rows_after,
  dropped_rows
FROM etl_run_log
ORDER BY run_at DESC
LIMIT 5;


/* ---------------------------------------------------------------------
   B) Power BI-friendly quick peeks (views)
------------------------------------------------------------------------ */
-- Overall KPI summary (single-row view for dashboard cards)
SELECT * FROM v_kpi_overall;

-- Sales & Profit by month
SELECT * FROM v_sales_profit_by_month ORDER BY order_month;

-- Month-over-month growth
SELECT * FROM v_sales_profit_mom ORDER BY order_month;

-- Region summary
SELECT * FROM v_region_performance ORDER BY total_profit DESC;

-- Region monthly trend
SELECT * FROM v_region_monthly ORDER BY order_month, region;

-- Region MoM trend
SELECT * FROM v_region_mom ORDER BY region, order_month;

-- Quality flags by month
SELECT * FROM v_quality_flags_by_month ORDER BY order_month;

-- ETL run history
SELECT * FROM v_etl_run_history ORDER BY run_at DESC;


/* ---------------------------------------------------------------------
   C) Business questions (Sales performance)
------------------------------------------------------------------------ */

-- Q1: Best months by profit
SELECT
  order_month,
  total_sales,
  total_profit
FROM v_sales_profit_by_month
ORDER BY total_profit DESC
LIMIT 12;

-- Q2: Which categories drive the most profit?
SELECT
  category,
  total_sales,
  total_profit,
  avg_discount
FROM v_category_performance
ORDER BY total_profit DESC;

-- Q3: Loss-making sub-categories (profit < 0)
SELECT
  category,
  sub_category,
  total_sales,
  total_profit,
  profit_margin,
  avg_discount
FROM v_subcategory_performance
WHERE total_profit < 0
ORDER BY total_profit ASC;

-- Q4: Top 15 customers by total sales
SELECT
  customer_id,
  customer_name,
  region,
  segment,
  total_sales,
  total_profit,
  orders_cnt
FROM v_top_customers
ORDER BY total_sales DESC
LIMIT 15;

-- Q5: High sales but low margin customers (example threshold)
SELECT
  customer_id,
  customer_name,
  region,
  total_sales,
  total_profit,
  ROUND(1.0 * total_profit / NULLIF(total_sales, 0), 4) AS profit_margin
FROM v_top_customers
WHERE total_sales >= 5000
ORDER BY profit_margin ASC
LIMIT 20;


/* ---------------------------------------------------------------------
   D) Business questions (Region performance)
------------------------------------------------------------------------ */

-- Q6: Rank regions by profit margin
SELECT
  region,
  total_sales,
  total_profit,
  profit_margin,
  avg_discount,
  avg_ship_days
FROM v_region_performance
ORDER BY profit_margin DESC;

-- Q7: Region contribution share (sales/profit)
WITH totals AS (
  SELECT
    SUM(total_sales)  AS all_sales,
    SUM(total_profit) AS all_profit
  FROM v_region_performance
)
SELECT
  r.region,
  r.total_sales,
  r.total_profit,
  ROUND(100.0 * r.total_sales  / NULLIF(t.all_sales, 0), 2)  AS sales_share_pct,
  ROUND(100.0 * r.total_profit / NULLIF(t.all_profit, 0), 2) AS profit_share_pct
FROM v_region_performance r
CROSS JOIN totals t
ORDER BY profit_share_pct DESC;

-- Q8: Which region is growing fastest MoM (latest month)
WITH latest AS (
  SELECT MAX(order_month) AS latest_month FROM v_sales_profit_by_month
)
SELECT
  rm.region,
  rm.order_month,
  rm.sales_mom_pct,
  rm.profit_mom_pct
FROM v_region_mom rm
JOIN latest l
  ON rm.order_month = l.latest_month
ORDER BY rm.profit_mom_pct DESC;


/* ---------------------------------------------------------------------
   E) Data quality angle (tie back to ETL flags)
------------------------------------------------------------------------ */

-- Q9: Months with highest high-discount rate
SELECT
  order_month,
  pct_high_discount,
  high_discount_rows,
  total_rows
FROM v_quality_flags_by_month
ORDER BY pct_high_discount DESC
LIMIT 12;

-- Q10: Sub-categories where high discounts concentrate
SELECT
  sub_category,
  pct_high_discount,
  high_discount_rows,
  total_rows,
  total_sales,
  total_profit
FROM v_quality_high_discount_subcat
ORDER BY high_discount_rows DESC
LIMIT 20;

-- End of 02_examples_queries.sql

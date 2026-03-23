-- Sample approved view definitions for the finance reporting schema.
-- These views represent the governed data layer that users query through
-- the Text-to-SQL interface. Production views live in Snowflake.

CREATE OR REPLACE VIEW finance_reporting.v_revenue AS
SELECT
    d.division,
    d.product_line,
    DATE_TRUNC('month', f.transaction_date) AS month,
    SUM(f.net_amount) AS revenue,
    SUM(f.cost_amount) AS cogs,
    SUM(f.quantity) AS units_sold
FROM fact_transactions f
JOIN dim_division d ON f.division_id = d.division_id
WHERE f.transaction_type = 'REVENUE'
GROUP BY d.division, d.product_line, DATE_TRUNC('month', f.transaction_date);


CREATE OR REPLACE VIEW finance_reporting.v_opex AS
SELECT
    cc.cost_center_name AS cost_center,
    DATE_TRUNC('month', b.period_date) AS month,
    SUM(a.amount) AS actual_opex,
    SUM(b.budget_amount) AS budget_opex,
    a.expense_category AS category
FROM fact_actuals a
JOIN dim_cost_center cc ON a.cost_center_id = cc.cost_center_id
LEFT JOIN fact_budget b ON a.cost_center_id = b.cost_center_id
    AND DATE_TRUNC('month', a.posting_date) = DATE_TRUNC('month', b.period_date)
    AND a.expense_category = b.expense_category
GROUP BY cc.cost_center_name, DATE_TRUNC('month', b.period_date), a.expense_category;


CREATE OR REPLACE VIEW finance_reporting.v_margin_by_division AS
SELECT
    division,
    month,
    revenue,
    cogs,
    CASE WHEN revenue > 0 THEN (revenue - cogs) / revenue ELSE 0 END AS gross_margin_pct
FROM finance_reporting.v_revenue;

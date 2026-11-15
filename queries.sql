-- Fuel station sales analysis (simulated data). Run on SQLite; tables: sales, stations.

-- Q1. Total revenue, transactions and average sale
SELECT COUNT(*) AS transactions,
       ROUND(SUM(amount)) AS revenue_ngn,
       ROUND(AVG(amount)) AS avg_sale_ngn
FROM sales;

-- Q2. Revenue and share by station
SELECT st.station_name, st.state,
       COUNT(*) AS transactions,
       ROUND(SUM(s.amount)) AS revenue_ngn,
       ROUND(100.0 * SUM(s.amount) / (SELECT SUM(amount) FROM sales), 1) AS revenue_share_pct
FROM sales s
JOIN stations st ON st.station_id = s.station_id
GROUP BY st.station_id
ORDER BY revenue_ngn DESC;

-- Q3. Revenue by product
SELECT product,
       COUNT(*) AS transactions,
       ROUND(SUM(amount)) AS revenue_ngn,
       ROUND(SUM(quantity), 1) AS units_sold
FROM sales
GROUP BY product
ORDER BY revenue_ngn DESC;

-- Q4. Monthly revenue with month-on-month change
WITH monthly AS (
    SELECT month, SUM(amount) AS revenue
    FROM sales
    GROUP BY month
)
SELECT month,
       ROUND(revenue) AS revenue_ngn,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month), 1) AS mom_change_pct
FROM monthly
ORDER BY month;

-- Q5. Payment method mix
SELECT payment_method,
       COUNT(*) AS transactions,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sales), 1) AS pct_of_transactions,
       ROUND(SUM(amount)) AS revenue_ngn
FROM sales
GROUP BY payment_method
ORDER BY transactions DESC;

-- Q6. Peak hours (transactions per hour of day)
SELECT hour, COUNT(*) AS transactions, ROUND(SUM(amount)) AS revenue_ngn
FROM sales
GROUP BY hour
ORDER BY hour;

-- Q7. Station ranking within each product (window function)
SELECT product, station_name, revenue_ngn,
       RANK() OVER (PARTITION BY product ORDER BY revenue_ngn DESC) AS rank_in_product
FROM (
    SELECT s.product, st.station_name, ROUND(SUM(s.amount)) AS revenue_ngn
    FROM sales s
    JOIN stations st ON st.station_id = s.station_id
    GROUP BY s.product, st.station_name
)
ORDER BY product, rank_in_product;

-- Q8. POS terminals with the lowest card share (possible terminal or network issues to investigate)
SELECT pos_terminal,
       COUNT(*) AS transactions,
       ROUND(100.0 * SUM(CASE WHEN payment_method = 'POS card' THEN 1 ELSE 0 END) / COUNT(*), 1) AS card_share_pct
FROM sales
GROUP BY pos_terminal
HAVING COUNT(*) > 500
ORDER BY card_share_pct ASC
LIMIT 5;

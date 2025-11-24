-- Revenue data by month showing Q3 2024 dip
-- This demonstrates the scenario: "Why is revenue down in Q3?"

-- Helper: Generate revenue records for 2024 (Jan-Sep)
-- Revenue shows healthy growth Q1-Q2, then dips in Q3 due to:
-- 1. TechCorp downgrade (APAC): -$14K MRR in July
-- 2. MediaCo churn (NA): -$15K MRR in May
-- 3. Seasonal slowdown in EMEA during summer
-- 4. Marketing Masters churn (NA): -$3K MRR in March

-- January 2024 - Starting strong
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr) VALUES
-- NA Enterprise (8 active customers)
(1, 1, '2024-01', 18000, 216000, 0, 0, 0, 0),
(2, 1, '2024-01', 15000, 180000, 0, 0, 0, 0),
(3, 1, '2024-01', 16500, 198000, 0, 0, 0, 0),
(4, 1, '2024-01', 19000, 228000, 0, 0, 0, 0),
(5, 1, '2024-01', 14000, 168000, 0, 0, 0, 0),
(6, 1, '2024-01', 15000, 180000, 0, 0, 0, 0),
(7, 1, '2024-01', 17000, 204000, 0, 0, 0, 0),
(8, 1, '2024-01', 20000, 240000, 20000, 0, 0, 0),  -- NEW customer in Jan

-- EMEA Enterprise (6 customers)
(31, 2, '2024-01', 16000, 192000, 0, 0, 0, 0),
(32, 2, '2024-01', 21000, 252000, 0, 0, 0, 0),
(33, 2, '2024-01', 18500, 222000, 0, 0, 0, 0),
(34, 2, '2024-01', 19500, 234000, 0, 0, 0, 0),
(35, 2, '2024-01', 17000, 204000, 0, 0, 0, 0),
(36, 2, '2024-01', 22000, 264000, 0, 0, 0, 0),

-- APAC Enterprise (including TechCorp at full $18K)
(56, 3, '2024-01', 20000, 240000, 0, 0, 0, 0),
(57, 3, '2024-01', 17500, 210000, 0, 0, 0, 0),
(58, 3, '2024-01', 16000, 192000, 0, 0, 0, 0),
(59, 3, '2024-01', 21500, 258000, 0, 0, 0, 0),
(60, 3, '2024-01', 18000, 216000, 0, 0, 0, 0),
(61, 3, '2024-01', 18000, 216000, 18000, 0, 0, 0),  -- TechCorp NEW in Jan

-- LATAM Enterprise
(78, 4, '2024-01', 15500, 186000, 0, 0, 0, 0),
(79, 4, '2024-01', 19000, 228000, 0, 0, 0, 0),
(80, 4, '2024-01', 16500, 198000, 0, 0, 0, 0),
(81, 4, '2024-01', 17500, 210000, 0, 0, 0, 0);

-- February through June (stable growth with small additions)
-- Note: Simplified - in real scenario would have all 100 customers
-- Focusing on key customers that drive the Q3 story

-- July 2024 - THE BIG DOWNGRADE
-- TechCorp (customer 61) downgrades from Enterprise ($18K) to Professional ($4K)
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr) VALUES
(61, 3, '2024-07', 4000, 48000, 0, 0, 14000, 0);  -- CONTRACTION: -$14K

-- August 2024 - Seasonal slowdown continues
-- EMEA summer vacation period reduces new sales

-- September 2024 - Q3 ends weak
-- Product team delays v2.0 release, customers waiting to upgrade

-- Summary stats for the "revenue down" query
-- Q1 2024 (Jan-Mar): Total MRR ~$585K, growing
-- Q2 2024 (Apr-Jun): Total MRR ~$595K, stable
-- Q3 2024 (Jul-Sep): Total MRR ~$540K, DOWN 9.2%
--   - TechCorp downgrade: -$14K (July)
--   - MediaCo churn: -$15K (May, affects Q2 end/Q3 start)
--   - Marketing Masters churn: -$3K (March)
--   - Seasonal EMEA slowdown: -$10K effective
--   - New customer additions: +$7K (insufficient to offset)

-- Full monthly revenue summary
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-02' as year_month,
    s.monthly_value as mrr,
    s.monthly_value * 12 as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    0 as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status = 'active'
    AND s.start_date <= '2024-02-29'
    AND (s.end_date IS NULL OR s.end_date > '2024-02-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month = '2024-01');

INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-03' as year_month,
    CASE
        WHEN s.customer_id = 14 THEN 0  -- Marketing Masters churned
        ELSE s.monthly_value
    END as mrr,
    CASE
        WHEN s.customer_id = 14 THEN 0
        ELSE s.monthly_value * 12
    END as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    CASE WHEN s.customer_id = 14 THEN 3000 ELSE 0 END as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status IN ('active', 'canceled')
    AND s.start_date <= '2024-03-31'
    AND (s.end_date IS NULL OR s.end_date >= '2024-03-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02'));

-- April - June (Q2 2024)
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-04' as year_month,
    s.monthly_value as mrr,
    s.monthly_value * 12 as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    0 as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status = 'active'
    AND s.start_date <= '2024-04-30'
    AND (s.end_date IS NULL OR s.end_date > '2024-04-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03'));

INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-05' as year_month,
    CASE
        WHEN s.customer_id = 6 THEN 0  -- MediaCo churned
        ELSE monthly_value
    END as mrr,
    CASE
        WHEN s.customer_id = 6 THEN 0
        ELSE monthly_value * 12
    END as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    CASE WHEN s.customer_id = 6 THEN 15000 ELSE 0 END as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status IN ('active', 'canceled')
    AND s.start_date <= '2024-05-31'
    AND (s.end_date IS NULL OR s.end_date >= '2024-05-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03', '2024-04'));

INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-06' as year_month,
    CASE
        WHEN s.customer_id = 24 THEN 0  -- Fitness Studio churned
        ELSE monthly_value
    END as mrr,
    CASE
        WHEN s.customer_id = 24 THEN 0
        ELSE monthly_value * 12
    END as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    CASE WHEN s.customer_id = 24 THEN 450 ELSE 0 END as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status IN ('active', 'canceled')
    AND s.start_date <= '2024-06-30'
    AND (s.end_date IS NULL OR s.end_date >= '2024-06-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03', '2024-04', '2024-05'));

-- Q3 2024 - The problematic quarter

-- July: TechCorp downgrade hits
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-07' as year_month,
    CASE
        WHEN s.customer_id = 61 THEN 4000  -- TechCorp downgraded to Professional
        ELSE monthly_value
    END as mrr,
    CASE
        WHEN s.customer_id = 61 THEN 48000
        ELSE monthly_value * 12
    END as arr,
    CASE WHEN s.customer_id = 100 THEN 510 ELSE 0 END as new_mrr,  -- New customer
    0 as expansion_mrr,
    CASE WHEN s.customer_id = 61 THEN 14000 ELSE 0 END as contraction_mrr,  -- -$14K!
    0 as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status = 'active'
    AND s.start_date <= '2024-07-31'
    AND (s.end_date IS NULL OR s.end_date > '2024-07-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06'));

-- August: EMEA summer slump
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-08' as year_month,
    s.monthly_value as mrr,
    s.monthly_value * 12 as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    0 as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status = 'active'
    AND s.start_date <= '2024-08-31'
    AND (s.end_date IS NULL OR s.end_date > '2024-08-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07'));

-- September: Q3 ends weak
INSERT INTO revenue (customer_id, region_id, year_month, mrr, arr, new_mrr, expansion_mrr, contraction_mrr, churned_mrr)
SELECT
    s.customer_id,
    c.region_id,
    '2024-09' as year_month,
    s.monthly_value as mrr,
    s.monthly_value * 12 as arr,
    0 as new_mrr,
    0 as expansion_mrr,
    0 as contraction_mrr,
    0 as churned_mrr
FROM subscriptions s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.status = 'active'
    AND s.start_date <= '2024-09-30'
    AND (s.end_date IS NULL OR s.end_date > '2024-09-01')
    AND s.customer_id NOT IN (SELECT customer_id FROM revenue WHERE year_month IN ('2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'));

-- Northwind Analytics Data Warehouse Schema
-- Synthetic data for BI analytics example
-- Database: SQLite (can be adapted for DuckDB/PostgreSQL)

-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    region_id INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL,
    region_code TEXT NOT NULL UNIQUE,
    quota_mrr REAL NOT NULL
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry TEXT,
    segment TEXT NOT NULL CHECK(segment IN ('Enterprise', 'Professional', 'Starter')),
    region_id INTEGER NOT NULL,
    signup_date DATE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'churned', 'trial')),
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    plan_name TEXT NOT NULL,
    monthly_value REAL NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status TEXT NOT NULL CHECK(status IN ('active', 'canceled', 'paused')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Revenue table (monthly aggregated)
CREATE TABLE IF NOT EXISTS revenue (
    revenue_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    year_month TEXT NOT NULL,  -- Format: YYYY-MM
    mrr REAL NOT NULL,
    arr REAL NOT NULL,
    new_mrr REAL DEFAULT 0,
    expansion_mrr REAL DEFAULT 0,
    contraction_mrr REAL DEFAULT 0,
    churned_mrr REAL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

-- Product usage metrics
CREATE TABLE IF NOT EXISTS usage_metrics (
    metric_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    metric_date DATE NOT NULL,
    dashboards_created INTEGER DEFAULT 0,
    queries_executed INTEGER DEFAULT 0,
    reports_generated INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Customer health scores
CREATE TABLE IF NOT EXISTS customer_health (
    health_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    as_of_date DATE NOT NULL,
    health_score INTEGER NOT NULL CHECK(health_score BETWEEN 0 AND 100),
    product_usage_score INTEGER CHECK(product_usage_score BETWEEN 0 AND 100),
    support_satisfaction_score INTEGER CHECK(support_satisfaction_score BETWEEN 0 AND 100),
    payment_health INTEGER CHECK(payment_health IN (0, 1)),
    days_since_last_login INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_revenue_year_month ON revenue(year_month);
CREATE INDEX IF NOT EXISTS idx_revenue_region ON revenue(region_id);
CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region_id);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_health_customer ON customer_health(customer_id);

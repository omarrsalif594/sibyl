# Scenario 2: Revenue Forecast by Category

## Business Problem

Acme Shop's inventory manager needs to forecast future revenue by product category to make informed purchasing decisions. Key challenges:
- **Seasonal patterns**: Camping gear peaks in summer, drops in winter
- **Category differences**: Apparel has steadier demand than camping equipment
- **Inventory planning**: Need 2-3 months lead time for bulk orders
- **Budget allocation**: Marketing spend should align with expected revenue

Without accurate forecasts, the company either overstocks (tying up cash) or understocks (losing sales).

## Solution

Implement a time-series forecasting pipeline using Chronulus MCP that:
1. Queries historical order data from SQLite database
2. Aggregates daily orders into monthly revenue by category
3. Constructs **TimeSeriesArtifact** (typed artifacts)
4. Calls **Chronulus MCP** for statistical forecasting
5. Returns forecast with confidence intervals and actionable insights

## Required Setup

### Data Sources
- **Orders Database**: SQLite at `data/sql/acme_shop.db`
  - 1,000 orders over 24 months (2023-2024)
  - 5 categories: Camping, Apparel, Footwear, Backpacks, Accessories
  - Realistic seasonality baked into synthetic data

### Infrastructure
- **SQL Provider**: SQLite (no external dependencies)
- **MCP Server**: Chronulus for forecasting
  - Install: `pip install chronulus-mcp`
  - Start: Runs automatically via stdio transport

### Environment Variables
```bash
export CHRONULUS_API_KEY="your-key-here"
# Note: For demo, uses simulated forecast if Chronulus not available
```

## Running the Pipeline

```bash
# Navigate to Acme Shop directory
cd examples/companies/acme_shop

# Forecast specific category
python pipelines/revenue_forecast.py --category Camping --periods 12
python pipelines/revenue_forecast.py --category Apparel --periods 12

# Forecast all categories combined
python pipelines/revenue_forecast.py --all --periods 30

# Longer forecast horizon
python pipelines/revenue_forecast.py --category Camping --periods 24
```

## Expected Output

```
================================================================================
ACME SHOP - REVENUE FORECASTING PIPELINE
================================================================================
Category: Camping
Forecast Periods: 12 months

Step 1: Querying historical revenue data...
  Retrieved 296 days of data
  Aggregated to 24 months

Building TimeSeriesArtifact...
  Created artifact with 24 monthly data points
  Time range: 2023-01-01 to 2024-12-01
  Value range: $989.94 to $10489.56

Calling Chronulus MCP to forecast 12 periods...
  Forecast generated: 12 periods
  Model: prophet
  MAE: $250.50

================================================================================
ACME SHOP - REVENUE FORECAST REPORT
================================================================================

Category: Camping
Generated: 2025-11-22 18:06:49

--------------------------------------------------------------------------------
HISTORICAL DATA
--------------------------------------------------------------------------------
Time Series: 2023-01-01 to 2024-12-01
Frequency: monthly
Points: 24
Min: $989.94, Max: $10489.56, Avg: $4178.53

Sample Points:
  2023-01: $989.94
  2023-05: $4019.78
  2023-09: $2809.87
  2024-01: $1389.93
  2024-05: $4269.80
  2024-09: $4249.75

--------------------------------------------------------------------------------
FORECAST
--------------------------------------------------------------------------------
Time Series: 2025-01-01 to 2025-12-01
Frequency: monthly
Points: 12
Min: $3850.50, Max: $5621.80, Avg: $4512.40

Sample Points:
  2025-01: $3850.50 (CI: $3272.93-$4428.08)
  2025-03: $4125.30 (CI: $3506.51-$4744.10)
  2025-06: $5621.80 (CI: $4778.53-$6465.07)
  2025-07: $5450.25 (CI: $4632.71-$6267.79)
  2025-09: $4312.15 (CI: $3665.33-$4958.97)
  2025-12: $3995.60 (CI: $3396.26-$4594.94)

--------------------------------------------------------------------------------
KEY INSIGHTS
--------------------------------------------------------------------------------
• Last historical month revenue: $1,039.92
• Average forecasted monthly revenue: $4,512.40
• Expected change: +334.1%
• Peak forecasted month: June 2025 ($5,621.80)

================================================================================

Full result saved to: output/revenue_forecast_Camping_12mo.json
```

## What's Demonstrated

### Sibyl Features - Core Focus

#### 1. TimeSeriesArtifact (Typed Artifacts)

This scenario is the **primary demonstration** of TimeSeriesArtifact:

```python
from sibyl.core.artifacts.timeseries import (
    TimeSeriesArtifact,
    TimePoint,
    TimeSeriesFrequency
)

# Build from SQL query results
time_points = [
    TimePoint(
        timestamp=datetime(2023, 1, 1),
        value=5420.50,
        properties={"category": "Camping", "is_historical": True}
    ),
    # ... more points
]

artifact = TimeSeriesArtifact(
    data=time_points,
    frequency=TimeSeriesFrequency.MONTHLY,
    metadata={
        "source": "acme_shop_orders",
        "category": "Camping",
        "unit": "USD"
    }
)

# Use artifact methods
time_range = artifact.get_time_range()
value_range = artifact.get_value_range()
summary = artifact.summarize_for_llm(max_points=10)
```

Key methods demonstrated:
- `from_simple_list()`: Build from timestamp/value lists
- `from_mcp_response()`: Parse Chronulus forecast response
- `get_time_range()`: Extract temporal bounds
- `get_value_range()`: Extract value bounds
- `summarize_for_llm()`: Generate LLM-friendly summary
- `to_dict()`: Serialize for JSON output
- `to_duckdb_compatible()`: Prepare for database storage

#### 2. Chronulus MCP Integration

```python
# Call Chronulus via MCP adapter
forecast = call_chronulus_mcp(
    historical_data=artifact,
    forecast_periods=12
)

# Returns TimeSeriesArtifact with:
# - Forecast values
# - Confidence intervals (upper/lower bounds)
# - Model metadata (algorithm, accuracy metrics)
# - Forecast-specific properties
```

#### 3. SQL Data Provider

```python
# Query orders database
cursor.execute("""
    SELECT DATE(o.order_date) as order_date,
           SUM(oi.line_total) as daily_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN categories c ON p.category_id = c.category_id
    WHERE c.name = ?
    GROUP BY DATE(o.order_date)
    ORDER BY order_date
""", [category])
```

### E-commerce Patterns
- Historical sales analysis
- Seasonal pattern detection
- Multi-category forecasting
- Confidence interval reporting
- Inventory planning support

## Performance Metrics

- **SQL Query**: <100ms for 1000 orders
- **Aggregation**: <10ms to monthly data
- **TimeSeriesArtifact Creation**: <1ms
- **Chronulus Forecast**: 2-10 seconds (depends on model)
- **Total Pipeline**: <15 seconds

## Data Characteristics

### Seasonality by Category

| Category    | Summer Peak | Winter Drop | Annual Avg |
|-------------|-------------|-------------|------------|
| Camping     | +150%       | -60%        | $4,180     |
| Apparel     | +30%        | +10%        | $3,780     |
| Footwear    | +60%        | -30%        | $2,650     |
| Backpacks   | +80%        | -40%        | $2,980     |
| Accessories | +40%        | -20%        | $1,900     |

### Historical Trends (2023-2024)
- **Camping**: Strong seasonality, growing trend (+15% YoY)
- **Apparel**: Steady demand, slight seasonal variation
- **Footwear**: Moderate seasonality, stable trend
- **Backpacks**: Strong summer peak, recovering winter
- **Accessories**: Low seasonality, consistent sales

## Use Cases

### Inventory Management
```bash
# 3-month forecast for purchasing decisions
python pipelines/revenue_forecast.py --category Camping --periods 3

# Action: Order $15,000 of camping gear for spring season
```

### Marketing Budget Allocation
```bash
# 6-month forecast across all categories
python pipelines/revenue_forecast.py --all --periods 6

# Action: Allocate 40% of summer ad spend to Camping
```

### Financial Planning
```bash
# Annual forecast for budget review
python pipelines/revenue_forecast.py --all --periods 12

# Action: Set revenue targets and margin goals
```

## Extensions

### Possible Enhancements
1. **Prophet model tuning**: Adjust seasonality parameters per category
2. **Multi-variate forecasting**: Include marketing spend, weather data
3. **Anomaly detection**: Flag unusual patterns in historical data
4. **What-if scenarios**: Model impact of promotions or price changes
5. **Confidence calibration**: Validate forecast accuracy over time
6. **Hierarchical forecasting**: Total → Category → Product forecasts
7. **External factors**: Include holidays, competitor sales, economic indicators

### Integration Points
- ERP system for automated purchasing
- BI dashboards (Tableau, PowerBI)
- Financial reporting tools
- Marketing automation platforms
- Real-time alerts for forecast deviations

## Testing Notes

The pipeline includes **fallback** for offline testing:
- If Chronulus MCP is not available, uses simulated forecast
- Simulated forecast includes seasonality and trend
- Confidence intervals generated using ±15% range
- Useful for development and testing without API keys

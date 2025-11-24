# Scenario 3: Discount Optimization (Optional)

## Business Problem

Acme Shop's marketing team runs seasonal promotions but struggles to determine optimal discount levels. Key challenges:
- **Revenue vs Volume tradeoff**: Deep discounts increase sales but hurt margins
- **Category differences**: Price elasticity varies by product type
- **Margin targets**: Must maintain 35% gross margin company-wide
- **Competitive pressure**: Need to stay competitive while remaining profitable

Current approach is ad-hoc: "Try 20% off and see what happens." This leads to suboptimal outcomes.

## Solution

Implement an optimization pipeline using Solver MCP that:
1. Loads current pricing and historical price elasticity data
2. Defines optimization problem:
   - **Objective**: Maximize total revenue
   - **Constraints**: Maintain minimum gross margin, reasonable discount limits
3. Calls **Solver MCP** for constrained optimization
4. Returns recommended discount percentages per category
5. Projects expected revenue and margin outcomes

## Required Setup

### Data Sources
- **Pricing Database**: Current prices and costs per product
- **Elasticity Data**: Historical response to price changes
- **Margin Requirements**: Minimum acceptable margins

### Infrastructure
- **SQL Provider**: SQLite for pricing data
- **MCP Server**: Solver for optimization
  - Install: `pip install solver-mcp`
  - Start: Runs automatically via stdio transport

### Environment Variables
```bash
export SOLVER_API_KEY="your-key-here"
```

## Problem Formulation

### Decision Variables
For each category `c`:
- `discount_c`: Discount percentage (0-50%)

### Objective Function
Maximize total revenue:
```
maximize: sum_c (base_revenue_c * (1 - discount_c) * demand_multiplier_c(discount_c))
```

Where `demand_multiplier_c` is derived from price elasticity.

### Constraints
1. **Margin constraint**:
   ```
   weighted_avg_margin >= 0.35  (35%)
   ```

2. **Discount bounds**:
   ```
   0 <= discount_c <= 0.50  (0-50%)
   ```

3. **Minimum discounts for key categories**:
   ```
   discount_Camping >= 0.10  (at least 10% for seasonal boost)
   ```

## Running the Pipeline

```bash
# Navigate to Acme Shop directory
cd examples/companies/acme_shop

# Run discount optimization
python pipelines/discount_optimizer.py --target-margin 0.35 --season summer

# With custom constraints
python pipelines/discount_optimizer.py \
  --target-margin 0.38 \
  --max-discount 0.40 \
  --min-camping-discount 0.15 \
  --season spring
```

## Expected Output

```
================================================================================
ACME SHOP - DISCOUNT OPTIMIZATION
================================================================================

Season: summer
Target Gross Margin: 35.0%
Current Average Discount: 15%

Calling Solver MCP for optimization...
  Problem: Linear Programming
  Variables: 5 (one per category)
  Constraints: 7
  Solution Status: OPTIMAL

================================================================================
RECOMMENDED DISCOUNTS
================================================================================

Category          Current    Optimal    Change    Expected Impact
---------------------------------------------------------------------------
Camping           15%        25%        +10%      +$8,400 revenue
Apparel           10%        18%        +8%       +$2,100 revenue
Footwear          20%        22%        +2%       +$800 revenue
Backpacks         12%        20%        +8%       +$1,600 revenue
Accessories       5%         15%        +10%      +$900 revenue

================================================================================
PROJECTED OUTCOMES
================================================================================

Metric                    Current          Optimized        Change
---------------------------------------------------------------------------
Total Monthly Revenue     $28,450          $42,250          +48.5%
Gross Margin              37.2%            35.0%            -2.2pp
Net Revenue (after disc)  $26,180          $36,025          +37.6%
Volume Increase                            +62%

ROI: For every $1 in discounts, expect $2.85 in incremental profit

================================================================================
IMPLEMENTATION PLAN
================================================================================

1. Update pricing system with new discount rates
2. Schedule campaign to start Monday, June 1
3. Monitor daily for first week, adjust if needed
4. Target categories with highest sensitivity first (Camping)
5. Communicate value clearly in marketing materials

================================================================================
```

## What's Demonstrated

### Sibyl Features
1. **Solver MCP Integration**: Constrained optimization via MCP
2. **Structured Outputs**: Optimization results as typed artifacts
3. **SQL Integration**: Loading pricing and elasticity data
4. **Multi-objective optimization**: Balance revenue and margin

### Optimization Techniques
- Linear programming
- Constraint satisfaction
- Price elasticity modeling
- What-if scenario analysis

## Mathematical Details

### Price Elasticity Model

For each category, elasticity `e_c` is estimated from historical data:
```
e_c = % change in quantity / % change in price
```

Typical elasticities:
- **Camping**: -1.5 (elastic - sensitive to price)
- **Apparel**: -0.8 (moderately elastic)
- **Footwear**: -1.2 (elastic)
- **Backpacks**: -1.0 (unit elastic)
- **Accessories**: -0.6 (inelastic)

### Demand Multiplier

Given discount `d` and elasticity `e`:
```
demand_multiplier(d) = 1 + (e * d)
```

For Camping with 25% discount and elasticity -1.5:
```
demand_multiplier(0.25) = 1 + (-1.5 * 0.25) = 1.375  (37.5% volume increase)
```

### Margin Calculation

```
margin_c = (price_c * (1 - discount_c) - cost_c) / (price_c * (1 - discount_c))

weighted_margin = sum_c (revenue_c * margin_c) / total_revenue
```

## Extensions

### Advanced Features
1. **Multi-product optimization**: Individual product-level discounts
2. **Time-series integration**: Incorporate forecast into optimization
3. **Inventory constraints**: Don't promote out-of-stock items
4. **Customer segmentation**: Different discounts for different customer types
5. **A/B testing**: Optimize for learning vs exploitation tradeoff

### Scenario Analysis
```bash
# Conservative (higher margin)
python pipelines/discount_optimizer.py --target-margin 0.40

# Aggressive (market share grab)
python pipelines/discount_optimizer.py --target-margin 0.30 --max-discount 0.50

# Category-specific
python pipelines/discount_optimizer.py --focus Camping --target-margin 0.32
```

## Integration Points

### Marketing Automation
```python
# Send recommendations to marketing platform
result = run_discount_optimizer()

for category, discount in result["recommendations"].items():
    marketing_api.create_campaign(
        category=category,
        discount=discount,
        start_date="2025-06-01"
    )
```

### Pricing System
```python
# Auto-update pricing
for category, discount in result["recommendations"].items():
    pricing_db.update_discounts(
        category=category,
        discount=discount,
        effective_date="2025-06-01"
    )
```

## Validation

Before implementing:
1. **Sanity check**: Do recommendations make intuitive sense?
2. **Historical comparison**: How do recommendations compare to past successful campaigns?
3. **Risk analysis**: What if elasticity is mis-estimated by 20%?
4. **Gradual rollout**: Test on subset of products first
5. **Monitor closely**: Track actual results vs projections

## Status

**⚠️ This scenario is OPTIONAL and not yet implemented.**

To implement:
1. Create `pipelines/discount_optimizer.py`
2. Define elasticity data (can estimate from historical orders)
3. Integrate Solver MCP
4. Create tests

This scenario demonstrates how optimization MCPs can be used for business decisions. It complements the forecasting scenario by showing how to act on predictions.

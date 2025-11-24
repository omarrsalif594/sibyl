# Scenario 1: Why is Revenue Down in Q3?

## Problem Statement

The CEO noticed that Q3 2024 revenue growth significantly lagged expectations. The finance team confirmed MRR declined by approximately 9% compared to Q2. The leadership team needs to understand:

1. What specifically caused the revenue decline?
2. Which regions and customer segments were most affected?
3. What were the largest revenue impacts?
4. What actions should be taken to prevent further decline?

This scenario demonstrates Northwind Analytics' ability to combine structured financial data with unstructured business context to answer complex "why" questions.

## Business Context

**Timeline**: Q3 2024 (July - September 2024)

**Stakeholders**:
- CEO: Needs executive summary for board meeting
- CFO: Wants detailed breakdown by region and customer
- Customer Success: Needs to identify at-risk accounts
- Product Team: Looking for product-related churn drivers

**Data Sources**:
- `revenue` table: Monthly MRR, expansions, contractions, churn
- `customers` and `subscriptions` tables: Customer details and contract info
- Product documentation: Revenue definitions, known Q3 issues, business context

## Setup Required

### 1. Initialize the Database

```bash
cd examples/companies/northwind_analytics/data/sql
python init_database.py
```

This creates `northwind_analytics.db` with:
- 100 customers across 4 regions
- Realistic subscription data
- Monthly revenue records showing Q3 decline
- Key events: TechCorp downgrade (-$14K MRR), MediaCo churn (-$15K MRR)

### 2. Index Documentation

The product documentation needs to be vectorized for semantic search:

```bash
cd examples/companies/northwind_analytics

# This would typically run a separate pipeline to embed and index docs
# For this demo, the pipeline handles it automatically
```

### 3. Verify Data

```bash
sqlite3 data/sql/northwind_analytics.db

-- Check revenue summary
SELECT
    year_month,
    SUM(mrr) as total_mrr,
    SUM(new_mrr) as new,
    SUM(expansion_mrr) as expansion,
    SUM(contraction_mrr) as contraction,
    SUM(churned_mrr) as churn
FROM revenue
WHERE year_month IN ('2024-06', '2024-07', '2024-08', '2024-09')
GROUP BY year_month
ORDER BY year_month;
```

Expected output:
```
2024-06 | 595000 | 0 | 0 | 0 | 450
2024-07 | 541000 | 510 | 0 | 14000 | 0    <- TechCorp downgrade
2024-08 | 541000 | 0 | 0 | 0 | 0
2024-09 | 541000 | 0 | 0 | 0 | 0
```

## Command to Run

### Basic Usage

```bash
cd examples/companies/northwind_analytics

sibyl pipeline run revenue_analysis \
  --workspace config/workspace.yaml \
  --input question="Why is revenue down in Q3?" \
  --input time_period="2024-Q3" \
  --output-file results/q3_revenue_analysis.json
```

### With Region Filter

```bash
sibyl pipeline run revenue_analysis \
  --workspace config/workspace.yaml \
  --input question="Why did APAC revenue drop in Q3?" \
  --input time_period="2024-Q3" \
  --input region="APAC" \
  --output-file results/apac_q3_analysis.json
```

### Verbose Mode (Debug)

```bash
sibyl pipeline run revenue_analysis \
  --workspace config/workspace.yaml \
  --input question="Why is revenue down in Q3?" \
  --input time_period="2024-Q3" \
  --verbose \
  --trace-id "rev-analysis-001"
```

## Expected Output

### Summary Statistics

```json
{
  "analysis": {
    "summary": "Q3 2024 MRR declined from $595K to $541K (-9.1%). Primary driver: TechCorp downgrade from Enterprise to Professional in July, resulting in $14K MRR contraction. Secondary factor: MediaCo churn in May (-$15K) carried into Q3.",
    "key_findings": [
      "Total MRR contraction: $54K (-9.1%)",
      "APAC region most impacted: -$14K (TechCorp downgrade) [revenue_definitions.md]",
      "Enterprise segment lost $14K MRR from single account",
      "EMEA seasonal slowdown: $0 new MRR in August [revenue_definitions.md]"
    ],
    "contributing_factors": [
      {
        "factor": "TechCorp downgrade (APAC Enterprise → Professional)",
        "impact_mrr": -14000,
        "percentage": 25.9,
        "citation": "revenue_definitions.md - Q3 Revenue Analysis Note"
      },
      {
        "factor": "MediaCo churn (NA Enterprise, May 2024)",
        "impact_mrr": -15000,
        "percentage": 27.8,
        "citation": "revenue_definitions.md"
      },
      {
        "factor": "EMEA seasonal effect (summer vacation period)",
        "impact_mrr": -10000,
        "percentage": 18.5,
        "citation": "revenue_definitions.md - Q3 factors"
      },
      {
        "factor": "Product transition delay (customers awaiting v2.0)",
        "impact_mrr": -5000,
        "percentage": 9.3,
        "citation": "revenue_definitions.md - Action Items"
      }
    ],
    "recommendations": [
      "Implement enhanced retention program for at-risk Enterprise accounts (prevent future TechCorp scenarios)",
      "Accelerate v2.0 feature releases to unlock waiting upgrades",
      "Expand self-service onboarding to reduce EMEA seasonal impact",
      "Conduct TechCorp win-back campaign with v2.0 upgrade path"
    ]
  },
  "data": {
    "q2_mrr": 595000,
    "q3_mrr": 541000,
    "change_mrr": -54000,
    "change_percentage": -9.08,
    "by_region": {
      "APAC": {
        "q2_mrr": 111000,
        "q3_mrr": 97000,
        "change": -14000
      },
      "North America": {
        "q2_mrr": 270000,
        "q3_mrr": 255000,
        "change": -15000
      },
      "EMEA": {
        "q2_mrr": 140000,
        "q3_mrr": 130000,
        "change": -10000
      },
      "LATAM": {
        "q2_mrr": 74000,
        "q3_mrr": 59000,
        "change": -15000
      }
    }
  },
  "sources": [
    {
      "document": "revenue_definitions.md",
      "section": "Q3 Revenue Analysis Note",
      "relevance_score": 0.94
    },
    {
      "document": "kpi_calculation_methods.md",
      "section": "Monthly Recurring Revenue (MRR)",
      "relevance_score": 0.87
    }
  ],
  "quality_score": 0.92
}
```

### Console Output Example

```
[INFO] Loading workspace: config/workspace.yaml
[INFO] Initializing pipeline: revenue_analysis
[INFO] Step 1/6: expand_query
  → Expanded query: revenue decline Q3 2024 MRR growth rate churn contraction
[INFO] Step 2/6: retrieve_docs
  → Retrieved 5 documents (relevance: 0.82-0.94)
[INFO] Step 3/6: query_revenue_data
  → Executing SQL: SELECT year_month, SUM(mrr) as total_mrr...
  → Returned 9 rows
[INFO] Step 4/6: add_citations
  → Added 3 citations to context
[INFO] Step 5/6: generate_analysis
  → Generated 847 tokens
[INFO] Step 6/6: validate_response
  → Quality score: 0.92 ✓
[SUCCESS] Pipeline completed in 23.4s

Analysis: Q3 2024 MRR declined from $595K to $541K (-9.1%)...
```

## What This Demonstrates

### 1. **Multi-Source Data Integration**
- **SQL Data**: Quantitative revenue metrics from data warehouse
- **Markdown Docs**: Business context, definitions, known issues
- **Vector Search**: Semantic matching to find relevant documentation

### 2. **RAG Pipeline Techniques**
- Query expansion (understand user intent)
- Document retrieval (find relevant context)
- Reranking (prioritize most relevant info)
- Citation injection (link facts to sources)

### 3. **SQL Integration**
- Parameterized queries (safe, no SQL injection)
- Complex aggregations (revenue by region, time period)
- Join operations (customers, subscriptions, revenue)

### 4. **LLM Generation**
- Chain-of-thought reasoning (analyze multiple factors)
- Structured output (JSON with specific fields)
- Citation-backed claims (every fact traced to source)

### 5. **Validation & Quality**
- Automated quality checks (has numbers, citations, recommendations)
- Scoring system (0-1 confidence)
- Error handling (graceful failures)

## Variations to Try

### 1. Compare Q2 vs Q3
```bash
sibyl pipeline run revenue_analysis \
  --input question="Compare Q2 and Q3 revenue performance" \
  --input time_period="2024-Q2,2024-Q3"
```

### 2. Segment-Specific Analysis
```bash
sibyl pipeline run revenue_analysis \
  --input question="Why did Enterprise customers churn in Q3?" \
  --input time_period="2024-Q3"
```

### 3. Regional Deep Dive
```bash
sibyl pipeline run revenue_analysis \
  --input question="What caused APAC revenue to decline?" \
  --input time_period="2024-Q3" \
  --input region="APAC"
```

### 4. Forward-Looking
```bash
sibyl pipeline run revenue_analysis \
  --input question="What revenue recovery actions should we prioritize for Q4?" \
  --input time_period="2024-Q4"
```

## Troubleshooting

### Database Not Found
```
Error: no such table: revenue
```
**Solution**: Run `python data/sql/init_database.py` to create the database.

### No Documents Retrieved
```
Warning: Retrieved 0 documents
```
**Solution**: Check that `data/docs/` contains markdown files. Verify paths in `workspace.yaml`.

### Quality Score Low
```
quality_score: 0.34
```
**Solution**:
- Check that LLM provider is configured (not just echo)
- Ensure documentation contains relevant Q3 information
- Verify SQL query returns non-empty results

### Pipeline Timeout
```
Error: Pipeline timed out after 180s
```
**Solution**: Increase timeout in `pipelines.yaml`:
```yaml
revenue_analysis:
  timeout_s: 300  # 5 minutes
```

## Next Steps

After running this scenario:

1. **Explore the data**: Query the SQLite database directly
2. **Modify the question**: Try different phrasing and time periods
3. **Add filters**: Experiment with region and segment filters
4. **Compare scenarios**: Run Scenario 2 (Dashboard Explanation) next
5. **Extend the pipeline**: Add custom steps for deeper analysis

## Learning Objectives

By completing this scenario, you will understand:

- ✅ How to combine SQL data with documentation context
- ✅ RAG pipeline architecture (retrieve → augment → generate)
- ✅ Vector search for semantic document retrieval
- ✅ LLM-powered analysis with citations
- ✅ Quality validation and scoring
- ✅ Real-world business intelligence use case

## Related Scenarios

- **Scenario 2**: Explain Dashboard (pure RAG, no SQL)
- **Scenario 3**: Generate Release Notes (structured + unstructured)
- **Scenario 4**: Customer Health Summary (SQL-heavy analysis)

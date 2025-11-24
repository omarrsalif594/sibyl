# Scenario 2: Explain this Dashboard to a New PM

## Problem Statement

A new product manager just joined Northwind Analytics and needs to quickly understand the company's dashboard features. They've been assigned to improve the "Revenue Overview" dashboard but have never used business intelligence tools before.

The PM asks: "Can someone explain the Revenue Overview dashboard to me? What do all these metrics mean? How do I actually use it?"

This scenario demonstrates pure RAG (Retrieval-Augmented Generation) - no SQL queries, just semantic search over documentation to provide beginner-friendly explanations.

## Business Context

**User**: New product manager (non-technical)

**Goal**:
- Understand what the dashboard shows
- Learn key metrics and what they mean
- Know how to interact with the dashboard
- Get practical tips for using it effectively

**Challenge**: Product documentation is comprehensive but written for all skill levels. The PM needs information filtered and explained at their level.

**Data Sources**:
- `dashboard_user_guide.md`: Detailed user guide for all dashboards
- `kpi_calculation_methods.md`: Technical definitions of metrics
- `feature_documentation.md`: Feature descriptions and use cases

## Setup Required

### 1. Verify Documentation

```bash
cd examples/companies/northwind_analytics

# Check that documentation exists
ls -la data/docs/

# Should see:
# - dashboard_user_guide.md
# - kpi_calculation_methods.md
# - revenue_definitions.md
# - feature_documentation.md
# - api_reference.md
```

### 2. No Database Required

Unlike Scenario 1, this is pure document retrieval - no SQL database needed!

### 3. Optional: Pre-index Documents

For better performance, you can pre-index the documentation:

```bash
# This would run a separate indexing pipeline
sibyl pipeline run index_documents \
  --workspace config/workspace.yaml \
  --input source="product_docs"
```

## Command to Run

### Basic Usage

```bash
cd examples/companies/northwind_analytics

sibyl pipeline run explain_dashboard \
  --workspace config/workspace.yaml \
  --input dashboard_name="Revenue Overview" \
  --input audience="new product manager" \
  --output-file results/dashboard_explanation.json
```

### Focus on Specific Features

```bash
sibyl pipeline run explain_dashboard \
  --workspace config/workspace.yaml \
  --input dashboard_name="Revenue Overview" \
  --input audience="new PM" \
  --input focus_areas='["metrics", "filters", "charts"]' \
  --output-file results/dashboard_metrics_explanation.json
```

### For Different Audiences

```bash
# For executives
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input audience="executive stakeholder"

# For analysts
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input audience="data analyst"

# For customers
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Customer Health" \
  --input audience="customer success manager"
```

## Expected Output

### Explanation for New PM

```json
{
  "explanation": "## Overview\n\nThe Revenue Overview dashboard is your command center for understanding how much money Northwind Analytics is making and where it's coming from. Think of it as a health monitor for the business - at a glance, you can see if revenue is growing, staying flat, or declining.\n\nThis dashboard shows three main things: (1) how much total recurring revenue we have right now, (2) how that's changed over time, and (3) how different regions and customer types are performing. It's designed to answer questions like \"Are we hitting our targets?\" and \"Where should we focus our efforts?\"\n\n## Key Metrics\n\n- **Total ARR (Annual Recurring Revenue)**: This is how much money we'd make in a year if all current customers kept paying us. For example, if we have $600K in ARR, that means our current customer base would generate $600,000 over the next 12 months. Higher is better! [dashboard_user_guide.md]\n\n- **Active Customers**: Simply the count of customers who currently have a paid subscription. This number should always be growing in a healthy business. [dashboard_user_guide.md]\n\n- **Monthly Growth Rate**: Shows how fast our revenue is growing month-over-month. A 5% growth rate means we're adding 5% more revenue each month. Anything above 3% is considered good for a SaaS company our size. [kpi_calculation_methods.md]\n\n- **Average Customer Value**: How much the typical customer pays us per month. This helps us understand if we're moving upmarket (larger customers) or downmarket (smaller customers). [revenue_definitions.md]\n\n## How to Use\n\n1. **Start with the metric cards at the top**: These give you the headline numbers. Look for green (good) or red (needs attention) indicators.\n\n2. **Check the trend chart in the middle**: This shows revenue over the last 12 months by default. Hover over any point to see exact numbers for that month. Is the line going up and to the right? Good! Flat or declining? Time to investigate.\n\n3. **Review the Regional Performance table**: This breaks down revenue by geography. Click on a region name to drill down and see which specific customers are driving that region's performance.\n\n4. **Apply filters if needed**: Use the filters in the top-right corner to focus on specific time periods (like Q3 2024) or customer segments (Enterprise, Professional, Starter).\n\n5. **Export if you need to share**: Click the download icon to export the current view as a PDF or CSV for presentations.\n\n## Pro Tips\n\n- **Use comparison mode**: Toggle \"Compare to previous period\" to see if things are getting better or worse. This is super helpful for spotting trends.\n\n- **Save your favorite views**: If you always look at \"Q3 Enterprise customers in EMEA,\" save that filter combination so you don't have to set it up every time.\n\n- **Check the data timestamp**: Look at the \"Last updated\" indicator in the bottom-right. Data refreshes nightly at 2 AM UTC, so yesterday's data should always be available.\n\n- **Don't panic over daily fluctuations**: Revenue can vary day-to-day. Focus on weekly and monthly trends instead of getting worried about single-day dips.\n\n- **Ask questions**: If a number doesn't make sense, click on it! Most metrics link to definitions or drill-down views with more context.",
  "sources": [
    {
      "document": "dashboard_user_guide.md",
      "section": "Overview Dashboard",
      "relevance_score": 0.96
    },
    {
      "document": "dashboard_user_guide.md",
      "section": "Key Metrics Cards",
      "relevance_score": 0.93
    },
    {
      "document": "kpi_calculation_methods.md",
      "section": "Sales & Revenue KPIs",
      "relevance_score": 0.89
    },
    {
      "document": "revenue_definitions.md",
      "section": "Annual Recurring Revenue (ARR)",
      "relevance_score": 0.87
    }
  ],
  "quality_score": 0.94
}
```

### Console Output

```
[INFO] Loading workspace: config/workspace.yaml
[INFO] Initializing pipeline: explain_dashboard
[INFO] Step 1/6: retrieve_documentation
  → Query: "Revenue Overview dashboard user guide features metrics"
  → Retrieved 8 documents (avg relevance: 0.88)
[INFO] Step 2/6: rerank_by_focus
  → Reranked to top 5 most relevant sections
[INFO] Step 3/6: chunk_documentation
  → Created 12 chunks (600 chars each, 80 overlap)
[INFO] Step 4/6: cite_sources
  → Added citations to 4 source documents
[INFO] Step 5/6: generate_explanation
  → Generated 623 tokens
  → Tone: Beginner-friendly ✓
  → Length: 487 words (target: 400-600) ✓
[INFO] Step 6/6: validate_explanation
  → Quality score: 0.94 ✓
  → Criteria met: 4/4
[SUCCESS] Pipeline completed in 18.2s

Dashboard explanation ready! See results/dashboard_explanation.json
```

## What This Demonstrates

### 1. **Pure RAG Architecture**
- No SQL queries - entirely document-based
- Semantic search to find relevant sections
- Multi-document synthesis into cohesive explanation

### 2. **Document Processing Pipeline**
- **Retrieval**: Find relevant docs using vector similarity
- **Reranking**: Prioritize most relevant sections
- **Chunking**: Break long documents into manageable pieces
- **Citation**: Link each claim back to source

### 3. **Audience Adaptation**
- Same documentation, different explanations
- Tone and complexity adjusted to audience
- Jargon translated to plain language
- Examples tailored to user's role

### 4. **Quality Validation**
- Length checks (not too short, not too long)
- Readability checks (beginner-friendly language)
- Structure checks (includes required sections)
- Example checks (has practical examples)

### 5. **RAG Techniques Used**

| Technique | Component | Purpose |
|-----------|-----------|---------|
| Query Expansion | `query_processor` | Broaden search with synonyms |
| Vector Search | `retriever` | Find semantically similar docs |
| Cross-Encoder Reranking | `reranker` | Refine relevance ordering |
| Semantic Chunking | `chunker` | Split docs at natural boundaries |
| Citation Injection | `augmenter` | Add source attribution |
| Controlled Generation | `generator` | Format and tone control |

## Variations to Try

### 1. Explain Different Dashboards

```bash
# Customer Health dashboard
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Customer Health" \
  --input audience="customer success manager"

# Pipeline Performance dashboard
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Pipeline Performance" \
  --input audience="sales leader"
```

### 2. Focus on Specific Features

```bash
# Just explain the filters
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input focus_areas='["filters"]'

# Explain interactions and shortcuts
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input focus_areas='["interactions", "keyboard shortcuts"]'
```

### 3. Different Expertise Levels

```bash
# For someone who's never used BI tools
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input audience="complete beginner"

# For an experienced analyst
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview" \
  --input audience="senior data analyst"
```

### 4. Compare Multiple Dashboards

```bash
# Explain differences between dashboards
sibyl pipeline run explain_dashboard \
  --input dashboard_name="Revenue Overview vs Customer Health" \
  --input audience="product manager" \
  --input focus_areas='["key differences", "when to use each"]'
```

## Troubleshooting

### No Documentation Found

```
Warning: Retrieved 0 documents for query
```

**Solution**:
1. Verify files exist: `ls data/docs/`
2. Check workspace config has correct path: `root: ./data/docs`
3. Ensure pattern matches: `pattern: "**/*.md"`

### Low Relevance Scores

```
Retrieved documents with low relevance (< 0.5)
```

**Solution**:
- Use more specific `dashboard_name` (e.g., "Revenue Overview" not "revenue")
- Add `focus_areas` to narrow search
- Check that documentation actually covers the dashboard

### Explanation Too Technical

```
Generated explanation too complex for beginner audience
```

**Solution**:
- Explicitly set `audience="complete beginner"`
- Adjust generator temperature in `workspace.yaml`: `temperature: 0.5`
- Add to prompt: "Avoid technical jargon"

### Missing Citations

```
quality_score: 0.62 (missing citations criterion)
```

**Solution**:
- Check that `cite_sources` step is executing
- Verify `augmenter` technique is configured
- Ensure generator prompt includes "Include citations"

## Comparison with Scenario 1

| Aspect | Scenario 1 (Revenue) | Scenario 2 (Dashboard) |
|--------|---------------------|------------------------|
| **Data Sources** | SQL + Docs | Docs only |
| **Pipeline Type** | Hybrid (DB + RAG) | Pure RAG |
| **Output** | Quantitative analysis | Qualitative explanation |
| **Techniques** | 6 steps, SQL generation | 6 steps, pure NLP |
| **Complexity** | High (multi-source) | Medium (single source) |
| **Use Case** | Answer "why" with data | Explain "how" and "what" |

## Next Steps

After running this scenario:

1. **Try different dashboards**: Each should have unique documentation
2. **Experiment with audiences**: See how explanations adapt
3. **Add focus areas**: Get targeted explanations for specific features
4. **Compare to manual docs**: Is the AI explanation clearer?
5. **Move to Scenario 3**: Generate release notes (combines structured + unstructured)

## Learning Objectives

By completing this scenario, you will understand:

- ✅ Pure RAG architecture without SQL
- ✅ Document retrieval and ranking
- ✅ Semantic chunking strategies
- ✅ Audience-adaptive generation
- ✅ Citation and source attribution
- ✅ Quality validation for generated text

## Related Scenarios

- **Scenario 1**: Revenue Analysis (SQL + RAG)
- **Scenario 3**: Generate Release Notes (structured data + RAG)
- **Scenario 4**: Customer Health Summary (SQL-heavy)

## Additional Resources

- **RAG Best Practices**: `docs/techniques/rag_pipeline/README.md`
- **Chunking Strategies**: `docs/techniques/rag_pipeline/chunking/`
- **Reranking Guide**: `docs/techniques/rag_pipeline/reranking/`

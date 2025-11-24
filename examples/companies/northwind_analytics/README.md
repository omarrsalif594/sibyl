# Northwind Analytics - Example Company

Realistic BI/Analytics SaaS demonstration for Sibyl

## Company Story

### About Northwind Analytics

Northwind Analytics is a fast-growing business intelligence SaaS platform serving mid-market companies across 4 global regions. Founded in 2021, the company helps businesses understand their data through interactive dashboards, custom reports, and automated insights.

**Current Status (Q3 2024)**:
- **100 customers** across Enterprise, Professional, and Starter segments
- **4 regions**: North America, EMEA, APAC, and LATAM
- **$541K MRR** (~$6.5M ARR)
- **Recent challenge**: Q3 revenue declined 9% due to customer downgrades and seasonal factors

The company's product combines:
- 📊 **Dashboard Builder**: Drag-and-drop visualization creation
- 🔍 **SQL Query Editor**: Custom data exploration
- 📧 **Scheduled Reports**: Automated delivery via email/Slack
- 🔗 **Data Connectors**: Snowflake, BigQuery, PostgreSQL, MySQL
- 🎨 **Embedded Analytics**: White-label dashboards for customer portals

**Team**:
- Product Team: Building new features (alerts, mobile apps, collaboration)
- Customer Success: Managing retention and expansion
- Finance: Tracking revenue metrics and forecasting
- Sales: Growing customer base across all regions

**Current Priorities**:
1. Understand and reverse Q3 revenue decline
2. Launch v2.0 with highly-requested features
3. Improve Enterprise customer retention
4. Expand into APAC and LATAM markets

---

## What This Example Demonstrates

This example showcases a **realistic analytics SaaS use case** that exercises:

### 1. **Data Connectors**
- ✅ `FilesystemMarkdownSource` for product documentation
- ✅ `SQLiteDataProvider` for data warehouse queries (easily swappable with DuckDB/PostgreSQL)
- ✅ `DuckDBVectorStore` for document embeddings and semantic search
- ✅ Optional MCP integration (NLP, RAG Memory)

### 2. **RAG Pipeline Techniques**
- ✅ Semantic chunking of markdown documentation
- ✅ Vector search with reranking
- ✅ Citation injection for source attribution
- ✅ Context augmentation for LLM prompts
- ✅ Multi-document synthesis

### 3. **Real-World Scenarios**
- ✅ **Scenario 1**: "Why is revenue down in Q3?" (SQL + RAG)
- ✅ **Scenario 2**: "Explain this dashboard to a new PM" (Pure RAG)
- ✅ **Scenario 3**: "Generate release notes" (Structured + Unstructured)
- ✅ **Scenario 4**: "Customer health summary" (SQL-heavy analytics)

### 4. **Production Patterns**
- ✅ Workspace configuration with multiple providers
- ✅ Technique shops for reusable pipeline components
- ✅ Input validation and error handling
- ✅ Quality scoring and validation
- ✅ Comprehensive smoke tests

---

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Sibyl installed**:
   ```bash
   pip install -e /path/to/sibyl
   ```
3. **Optional**: API keys for cloud LLM providers (for production use)
   ```bash
   export OPENAI_API_KEY=your-key
   export ANTHROPIC_API_KEY=your-key
   ```

### 1. Initialize the Data

```bash
cd examples/companies/northwind_analytics/data/sql
python init_database.py

# Should output:
# Creating database: northwind_analytics.db
# ✓ Schema created
# ✓ Seed data loaded
# ✓ Revenue data loaded
# Database summary:
#   Regions: 4
#   Customers: 100
#   Subscriptions: 100
#   Revenue records: 900
```

### 2. Run Your First Scenario

```bash
cd examples/companies/northwind_analytics

# Scenario 1: Analyze Q3 revenue decline
sibyl pipeline run revenue_analysis \
  --workspace config/workspace.yaml \
  --input question="Why is revenue down in Q3?" \
  --input time_period="2024-Q3"
```

**Expected output**: Comprehensive analysis showing TechCorp downgrade (-$14K MRR), seasonal effects, and recommendations.

### 3. Run Smoke Tests

```bash
# Verify everything is working
pytest tests/test_smoke.py -v

# Should pass all tests:
# ✓ test_workspace_loads
# ✓ test_markdown_docs_exist
# ✓ test_database_can_be_initialized
# ✓ test_pipeline_structure
# ... and more
```

---

## Scenarios

### Scenario 1: Why is Revenue Down in Q3?

**Problem**: Q3 2024 MRR declined 9% from $595K to $541K. CEO needs answers.

**What it exercises**:
- SQL queries against data warehouse
- RAG over revenue definitions documentation
- Multi-factor analysis with citations
- Quantitative + qualitative insights

**Run it**:
```bash
sibyl pipeline run revenue_analysis \
  --workspace config/workspace.yaml \
  --input question="Why is revenue down in Q3?" \
  --input time_period="2024-Q3" \
  --output-file results/q3_analysis.json
```

**Key findings** (from synthetic data):
- TechCorp downgrade: -$14K MRR (APAC Enterprise → Professional)
- MediaCo churn: -$15K MRR (NA Enterprise)
- EMEA seasonal slowdown: -$10K MRR
- Product v2.0 delay impacting upgrades

📖 **[Full Documentation](scenarios/01_revenue_down_q3.md)**

---

### Scenario 2: Explain Dashboard to New PM

**Problem**: New product manager needs to understand the "Revenue Overview" dashboard quickly.

**What it exercises**:
- Pure RAG (no SQL)
- Semantic search over user guides
- Audience-adaptive generation
- Beginner-friendly explanations

**Run it**:
```bash
sibyl pipeline run explain_dashboard \
  --workspace config/workspace.yaml \
  --input dashboard_name="Revenue Overview" \
  --input audience="new product manager" \
  --output-file results/dashboard_explanation.json
```

**Output**: Step-by-step guide explaining metrics, charts, filters, and pro tips in simple language.

📖 **[Full Documentation](scenarios/02_explain_dashboard.md)**

---

### Scenario 3: Generate Release Notes

**Problem**: Product team needs polished release notes for v2.1.0 (alerts, mobile app, collaboration).

**What it exercises**:
- Structured data (feature list) + unstructured docs
- Content organization and formatting
- Tone control (professional but friendly)
- Multi-document synthesis

**Run it**:
```bash
sibyl pipeline run generate_release_notes \
  --workspace config/workspace.yaml \
  --input version="v2.1.0" \
  --input release_date="2024-11-15" \
  --input feature_keywords='["alerts", "anomaly detection", "mobile app", "collaboration"]' \
  --output-file results/release_notes_v2.1.0.md
```

**Output**: Markdown release notes with emojis, user benefits, and proper formatting.

📖 **[Full Documentation](scenarios/03_generate_release_notes.md)**

---

### Scenario 4: Customer Health Summary (Bonus)

**Problem**: Identify at-risk customers based on health scores.

**What it exercises**:
- SQL-heavy analytics
- Health score calculations
- Customer segmentation
- Action recommendations for CS team

**Run it**:
```bash
sibyl pipeline run customer_health_summary \
  --workspace config/workspace.yaml \
  --input segment="Enterprise" \
  --input health_threshold=50 \
  --output-file results/health_summary.json
```

**Output**: List of at-risk customers with specific concerns and recommended actions.

---

## Project Structure

```
examples/companies/northwind_analytics/
├── README.md                    # This file
├── data/
│   ├── docs/                    # Markdown documentation (5 files)
│   │   ├── revenue_definitions.md
│   │   ├── dashboard_user_guide.md
│   │   ├── kpi_calculation_methods.md
│   │   ├── feature_documentation.md
│   │   └── api_reference.md
│   ├── sql/                     # SQL schema and data
│   │   ├── 01_schema.sql        # Tables: regions, customers, subscriptions, revenue
│   │   ├── 02_seed_data.sql     # 100 customers, realistic data
│   │   ├── 03_revenue_data.sql  # Monthly revenue with Q3 dip
│   │   └── init_database.py     # Database initialization script
│   └── logs/                    # Optional: sample application logs
├── config/
│   ├── workspace.yaml           # Provider and shop configuration
│   └── pipelines.yaml           # 4 pipeline definitions
├── scenarios/
│   ├── 01_revenue_down_q3.md    # Scenario 1 documentation
│   ├── 02_explain_dashboard.md  # Scenario 2 documentation
│   └── 03_generate_release_notes.md  # Scenario 3 documentation
├── tests/
│   └── test_smoke.py            # Smoke tests (pytest)
└── results/                     # Pipeline outputs (created on first run)
```

---

## Configuration Details

### Workspace Configuration

**File**: `config/workspace.yaml`

**Providers**:
- **document_sources.product_docs**: Markdown files in `data/docs/`
- **sql.analytics_warehouse**: SQLite database at `data/sql/northwind_analytics.db`
- **vector_store.docs_index**: DuckDB vector store for embeddings
- **llm.default**: Primary LLM (configurable: local/OpenAI/Anthropic)
- **llm.fast**: Fast LLM for simple queries
- **embeddings.default**: Sentence transformer for document vectorization

**Shops**:
- **rag_shop**: RAG pipeline techniques (chunking, retrieval, augmentation, reranking)
- **analytics_shop**: Data analysis techniques (query processing, generation, validation)
- **summarization_shop**: Summarization techniques

### Pipeline Configuration

**File**: `config/pipelines.yaml`

**Pipelines**:
1. `revenue_analysis`: 6-step pipeline combining SQL + RAG
2. `explain_dashboard`: 6-step pure RAG pipeline
3. `generate_release_notes`: 4-step content generation pipeline
4. `customer_health_summary`: SQL-heavy analysis pipeline

Each pipeline includes:
- Input validation (required/optional, types, defaults)
- Step definitions with technique usage
- Output mappings
- Timeout configuration

---

## Synthetic Data

### Data Warehouse Schema

**Tables**:
- **regions** (4 rows): NA, EMEA, APAC, LATAM with quotas
- **customers** (100 rows): Realistic company names, industries, segments
- **subscriptions** (100 rows): Active/churned subscriptions with pricing
- **revenue** (900 rows): Monthly MRR tracking Jan-Sep 2024
- **usage_metrics** (optional): Dashboard usage, API calls
- **customer_health** (optional): Health scores and component scores

### Revenue Data Story

**Q1 2024 (Jan-Mar)**:
- Starting MRR: ~$570K
- Healthy growth: +$15K net new MRR
- New customers: 8 (including TechCorp Enterprise at $18K/mo)

**Q2 2024 (Apr-Jun)**:
- Peak MRR: $595K (best quarter)
- Stable growth: +$10K net new
- Minor churn: Marketing Masters ($3K), Fitness Studio ($450)

**Q3 2024 (Jul-Sep)** - THE DIP:
- Ending MRR: $541K (-$54K, -9.1%)
- **Major event**: TechCorp downgrades Enterprise → Professional (July, -$14K)
- **Churn**: MediaCo (May carryover, -$15K)
- **Seasonal**: EMEA summer slowdown (August, -$10K effective)
- **Product delay**: v2.0 pushed to Q4, customers waiting

**Q4 2024 (Oct-Dec)** - RECOVERY (not in data):
- Expected: v2.0 launch, win-back campaigns, new customer acceleration

### Documentation Coverage

**5 Markdown files** (2,500+ lines total):
1. **revenue_definitions.md**: ARR, MRR, churn definitions + Q3 analysis note
2. **dashboard_user_guide.md**: How to use dashboards, filters, exports
3. **kpi_calculation_methods.md**: SQL formulas for all KPIs
4. **feature_documentation.md**: Dashboard builder, alerts, embedded analytics
5. **api_reference.md**: API endpoints, authentication, examples

All documents contain realistic business context and cross-reference each other.

---

## Testing

### Run Smoke Tests

```bash
cd examples/companies/northwind_analytics
pytest tests/test_smoke.py -v
```

**Test Coverage**:
- ✅ Workspace loading and validation
- ✅ Provider configuration
- ✅ Technique shop definitions
- ✅ Synthetic data integrity
- ✅ Database initialization
- ✅ Pipeline structure validation
- ✅ Scenario documentation completeness
- ✅ Integration (with mocked components)

**Expected Output**:
```
tests/test_smoke.py::TestNorthwindAnalyticsWorkspace::test_workspace_loads PASSED
tests/test_smoke.py::TestNorthwindAnalyticsWorkspace::test_workspace_has_providers PASSED
tests/test_smoke.py::TestSyntheticData::test_markdown_docs_exist PASSED
tests/test_smoke.py::TestSyntheticData::test_database_can_be_initialized PASSED
tests/test_smoke.py::TestRevenueAnalysisPipeline::test_pipeline_structure PASSED
...

======================== 15 passed in 3.42s =========================
```

### Manual Testing

#### Test Data Queries

```bash
# Query revenue data directly
sqlite3 data/sql/northwind_analytics.db

-- Q3 revenue summary
SELECT
    year_month,
    SUM(mrr) as total_mrr,
    SUM(contraction_mrr) as contractions,
    SUM(churned_mrr) as churn
FROM revenue
WHERE year_month >= '2024-07' AND year_month <= '2024-09'
GROUP BY year_month
ORDER BY year_month;

-- At-risk Enterprise customers
SELECT c.company_name, c.segment, s.monthly_value, s.status
FROM customers c
JOIN subscriptions s ON c.customer_id = s.customer_id
WHERE c.segment = 'Enterprise' AND s.status = 'active'
ORDER BY s.monthly_value DESC
LIMIT 10;
```

#### Test Documentation Search

```bash
# Search for Q3-related content
grep -r "Q3" data/docs/

# Verify all docs are readable
for file in data/docs/*.md; do
    echo "=== $file ==="
    head -5 "$file"
done
```

---

## Customization

### Using Real LLM Providers

Edit `config/workspace.yaml`:

```yaml
providers:
  llm:
    default:
      provider: anthropic  # or openai
      model: claude-3-5-sonnet-20241022  # or gpt-4
      api_key_env: ANTHROPIC_API_KEY
      temperature: 0.1

    fast:
      provider: openai
      model: gpt-3.5-turbo
      api_key_env: OPENAI_API_KEY
      temperature: 0.3
```

Then set API keys:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

### Using Different Databases

**PostgreSQL**:
```yaml
sql:
  analytics_warehouse:
    type: postgresql
    config:
      host: localhost
      port: 5432
      database: northwind_analytics
      user: postgres
      password_env: PGPASSWORD
```

**DuckDB**:
```yaml
sql:
  analytics_warehouse:
    type: duckdb
    config:
      path: ./data/sql/northwind_analytics.duckdb
```

### Adding New Scenarios

1. Create pipeline in `config/pipelines.yaml`
2. Document in `scenarios/04_your_scenario.md`
3. Add smoke test in `tests/test_smoke.py`
4. Update this README

---

## Troubleshooting

### Database Not Found

**Error**: `no such table: revenue`

**Solution**:
```bash
cd data/sql
python init_database.py
# Verify: ls -lh northwind_analytics.db
```

### No Documents Retrieved

**Error**: `Retrieved 0 documents for query`

**Solution**:
- Check `data/docs/` has markdown files
- Verify workspace.yaml has correct path: `root: ./data/docs`
- Check file permissions: `chmod +r data/docs/*.md`

### Pipeline Timeout

**Error**: `Pipeline timed out after 180s`

**Solution**: Increase timeout in `config/pipelines.yaml`:
```yaml
revenue_analysis:
  timeout_s: 300  # 5 minutes
```

### Low Quality Scores

**Symptom**: `quality_score: 0.32`

**Causes**:
- Using local echo LLM (returns empty responses)
- Missing documentation context
- SQL query returning no results

**Solution**:
- Configure real LLM provider (see Customization)
- Verify database has data: `sqlite3 data/sql/northwind_analytics.db "SELECT COUNT(*) FROM revenue;"`
- Check logs: `sibyl pipeline run ... --verbose`

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'sibyl'`

**Solution**:
```bash
# Install Sibyl in development mode
cd /path/to/sibyl
pip install -e .

# Or install from PyPI
pip install sibyl-mcp
```

---

## Next Steps

### For Users

1. ✅ **Run all scenarios**: Get familiar with different use cases
2. ✅ **Modify inputs**: Try different questions, time periods, regions
3. ✅ **Explore the data**: Query the database directly
4. ✅ **Read the docs**: Understand the synthetic company story
5. ✅ **Adapt for your use case**: Replace synthetic data with real data

### For Developers

1. ✅ **Study the pipelines**: Understand step composition
2. ✅ **Explore technique usage**: See how RAG techniques combine
3. ✅ **Add custom techniques**: Extend with your own implementations
4. ✅ **Build new scenarios**: Create pipelines for other use cases
5. ✅ **Contribute back**: Share improvements with the Sibyl community

### Extending This Example

**Add More Scenarios**:
- Sales pipeline analysis
- Customer churn prediction
- Product usage analytics
- Competitive intelligence

**Integrate Real Data**:
- Replace SQLite with your data warehouse
- Use actual product documentation
- Connect to production metrics

**Add MCPs**:
- MCP-NLP for entity extraction
- MCP-Memory for session context
- Custom MCPs for domain-specific tools

---

## Resources

### Documentation

- **Sibyl Docs**: `docs/README.md` in the Sibyl repository
- **Workspace Guide**: `docs/workspaces/README.md`
- **Pipeline Guide**: `docs/pipelines/README.md`
- **Technique Reference**: `docs/techniques/`

### Related Examples

- **Golden Path**: `examples/golden_path/` - Web research with RAG
- **Data Connectors**: `config/workspaces/data_connectors_example.yaml`
- **SQL + Docs**: `config/workspaces/sql_docs_pgvector.yaml`

### Support

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions and share ideas
- **Examples**: Browse other example companies

---

## License

Apache License 2.0 - see repository root for details

---

## Acknowledgments

This example was created to demonstrate:
- Real-world BI/analytics use cases
- Multi-source data integration (SQL + Docs + Vectors)
- RAG pipeline techniques in practice
- Production-ready configuration patterns

**Synthetic data is entirely fictional** and designed to tell a realistic story for educational purposes.

---

## Feedback

Found this example helpful? Have suggestions for improvements?

- Open an issue: `examples/companies/northwind_analytics/FEEDBACK.md`
- Submit a PR: Add new scenarios or improve existing ones
- Share your adaptations: Show us what you built!

**Happy building!** 🚀

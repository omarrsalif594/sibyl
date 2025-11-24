# BrightOps Agency - Knowledge Worker Automation Example

Demonstrating how Sibyl transforms messy, unstructured inputs into organized, actionable outputs using AI generation techniques and MCPs.

## The Story

**BrightOps** is a digital consultancy that builds web and mobile applications for startups and enterprises. Like many agencies, they face a constant challenge:

**Information Chaos**
- Kickoff meetings produce pages of unstructured notes
- Client emails reveal preferences... if you read between the lines
- Sales inquiries need detailed proposals, fast
- Knowledge lives in people's heads, not systems

**Manual Knowledge Work**
- PMs spend hours organizing meeting notes into project plans
- Team members re-learn client preferences on every project
- Proposal writing takes 8-10 hours per opportunity
- Institutional knowledge is lost when people leave

**This is exactly what Sibyl is designed to solve.**

## What This Example Demonstrates

BrightOps uses Sibyl to automate three critical knowledge worker workflows:

### 1. Meeting Notes → Structured Project Plan
**Problem:** 90-minute kickoff produces chaotic meeting notes
**Solution:** AI generation techniques organize into categories and milestones
**Time Saved:** 3 hours → 20 minutes per meeting
**Techniques:** `category_naming`, `checkpoint_naming`, Sequential Thinking MCP

### 2. Client Emails → Learned Preferences
**Problem:** Each client has unique communication style and expectations
**Solution:** RAG + In-Memoria MCP learn and store patterns as `PatternArtifact`
**Time Saved:** 2-3 weeks → 5 minutes learning curve
**Techniques:** RAG pipeline, In-Memoria MCP, PatternArtifact

### 3. One-Liner → Detailed Project Breakdown
**Problem:** Sales needs detailed proposals quickly for every inquiry
**Solution:** Sequential Thinking expands scope, AI techniques structure output
**Time Saved:** 8 hours → 1 hour per proposal
**Techniques:** Sequential Thinking MCP, `category_naming`, `checkpoint_naming`

## Quick Start

### Prerequisites

```bash
# 1. Ensure Node.js is installed (for MCP servers)
node --version  # Should be v16+

# 2. Install Sequential Thinking MCP (uses npx, no install needed)
# Installed automatically on first run

# 3. Install In-Memoria MCP (uses npx, no install needed)
# Installed automatically on first run

# 4. Ensure Sibyl is installed
pip install sibyl  # Or your installation method
```

### Setup

```bash
# Navigate to example directory
cd examples/companies/brightops_agency

# Create logs directory
mkdir -p logs

# Optional: Index documents for RAG (run once)
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline index_documents
```

### Run the Scenarios

#### Scenario 1: Meeting to Plan

```bash
# Turn messy Acme kickoff notes into structured plan
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline meeting_to_plan \
  --input '{"meeting_file": "kickoff_acme_mobile_2024_03.md"}'

# Try other meetings
--input '{"meeting_file": "brainstorm_techstart_website_2024_04.md"}'
--input '{"meeting_file": "status_update_globex_q2_2024.md"}'
--input '{"meeting_file": "retrospective_fintech_project_2024_03.md"}'
```

#### Scenario 2: Learn Client Preferences

```bash
# First, index documents for RAG
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline index_documents

# Learn Sarah's communication patterns (Acme CEO)
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline learn_preferences \
  --input '{"client_name": "Acme CEO Sarah"}'

# Learn other clients
--input '{"client_name": "TechStart Marcus"}'
--input '{"client_name": "Globex CTO Rachel"}'
```

#### Scenario 3: Project Breakdown

```bash
# Generate breakdown from one-liner
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "Build a mobile app for restaurant reservations",
    "timeline_weeks": 16
  }'

# Try other project ideas
--input '{"project_brief": "Healthcare patient portal with appointment booking"}'
--input '{"project_brief": "E-commerce platform for handmade crafts"}'
--input '{"project_brief": "Real-time inventory management system"}'
```

## Example Synthetic Data

This example includes realistic synthetic data:

### Meeting Notes (`data/docs/meetings/`)
- `kickoff_acme_mobile_2024_03.md` - Chaotic client kickoff (90 minutes)
- `brainstorm_techstart_website_2024_04.md` - Messy team brainstorm
- `status_update_globex_q2_2024.md` - Project status with risks
- `retrospective_fintech_project_2024_03.md` - Post-project lessons
- `discovery_healthtech_2024_05.md` - Q&A discovery session

### Client Emails (`data/docs/emails/`)
- `acme_ceo_communication_style.md` - Sarah (fast, brief, action-oriented)
- `techstart_detailed_feedback.md` - Marcus (formal, detailed, thorough)
- `globex_technical_preferences.md` - Rachel (technical, code-level)

### Project Specs (`data/docs/specs/`)
- `acme_restaurant_app_spec.md` - Detailed specification
- `fintech_dashboard_brief.md` - Brief overview
- `quick_project_idea.md` - Rough notes

### Brainstorms (`data/docs/brainstorms/`)
- `new_client_onboarding_ideas.md` - Stream of consciousness
- `agency_growth_strategy.md` - Strategic brainstorm

All data is **synthetic but realistic** - based on actual agency workflows.

## What Makes This Different

### Not Just RAG
Most "AI + documents" examples are just search and summarization. This example demonstrates:
- **Structured transformation** using Sibyl's AI generation techniques
- **Multi-step reasoning** with Sequential Thinking MCP
- **Persistent learning** with In-Memoria MCP
- **Typed artifacts** (PatternArtifact) not just JSON blobs

### Real Sibyl Techniques
This example uses actual techniques from `sibyl/techniques/ai_generation/`:
- `category_naming`: From formatting subtechniques
- `checkpoint_naming`: From formatting subtechniques
- `quality_scoring`: From validation subtechniques

These are **pluggable, reusable techniques** you can use in your own workflows.

### Real MCPs
- **Sequential Thinking**: Official Anthropic MCP for step-by-step reasoning
- **In-Memoria**: Official Anthropic MCP for persistent memory and pattern learning

## Folder Structure

```
examples/companies/brightops_agency/
├── README.md                          # This file
├── data/
│   └── docs/
│       ├── meetings/                  # 5 meeting transcripts
│       ├── emails/                    # 3 client email threads
│       ├── specs/                     # 3 project specifications
│       └── brainstorms/               # 2 brainstorm documents
├── config/
│   ├── workspace.yaml                 # MCP connections, techniques, data sources
│   └── pipelines.yaml                 # 3 scenario pipelines + indexing
├── scenarios/
│   ├── 01_meeting_to_plan.md         # Scenario 1 documentation
│   ├── 02_learn_client_preferences.md # Scenario 2 documentation
│   └── 03_project_breakdown.md        # Scenario 3 documentation
├── tests/
│   └── test_smoke.py                  # Smoke tests for all scenarios
└── logs/                              # Pipeline execution logs
```

## Key Techniques Reference

### category_naming
**Path:** `ai_generation.formatting.category_naming`
**What:** Organizes unstructured items into logical categories
**Use Case:** Feature lists → Work streams, Random ideas → Themes
**Config:**
```yaml
max_categories: 10
min_items_per_category: 2
use_hierarchical: false
```

### checkpoint_naming
**Path:** `ai_generation.formatting.checkpoint_naming`
**What:** Breaks projects into phased milestones with dependencies
**Use Case:** Work streams → Timeline, Features → Delivery plan
**Config:**
```yaml
max_checkpoints: 8
include_timeline: true
include_dependencies: true
```

### quality_scoring
**Path:** `ai_generation.validation.quality_scoring`
**What:** Scores outputs against quality criteria
**Use Case:** Validate AI output before human review
**Config:**
```yaml
min_score: 0.7
criteria:
  - completeness
  - clarity
  - actionability
```

### Sequential Thinking MCP
**Provider:** Anthropic official MCP
**What:** Multi-step reasoning, thought revision, branching logic
**Use Case:** Complex analysis, planning, validation
**Transport:** stdio via npx

### In-Memoria MCP
**Provider:** Anthropic official MCP
**What:** Persistent memory, pattern storage, graph entities
**Use Case:** Learning over time, institutional knowledge
**Transport:** stdio via npx

## Architecture Highlights

### Pipeline: `meeting_to_plan`
```
Load meeting doc
  → Sequential Thinking (analyze)
  → category_naming (organize)
  → checkpoint_naming (milestones)
  → Sequential Thinking (validate)
  → quality_scoring (score)
  → Format output
```

**Key Innovation:** Multi-step transformation with validation

### Pipeline: `learn_preferences`
```
RAG (search emails)
  → Sequential Thinking (analyze patterns)
  → In-Memoria (store entities)
  → PatternArtifact (typed output)
  → Summarize
```

**Key Innovation:** Persistent learning across sessions

### Pipeline: `project_breakdown`
```
Sequential Thinking (expand scope)
  → Sequential Thinking (explore architecture)
  → category_naming (work streams)
  → checkpoint_naming (milestones)
  → Sequential Thinking (estimate effort)
  → quality_scoring (validate)
  → Format breakdown
```

**Key Innovation:** Creative reasoning, not just templating

## Testing

### Run Smoke Tests

```bash
# Run all scenario tests
pytest examples/companies/brightops_agency/tests/test_smoke.py -v

# Run specific test
pytest examples/companies/brightops_agency/tests/test_smoke.py::test_meeting_to_plan -v
pytest examples/companies/brightops_agency/tests/test_smoke.py::test_learn_preferences -v
pytest examples/companies/brightops_agency/tests/test_smoke.py::test_project_breakdown -v
```

### Test Coverage
- Meeting to plan pipeline execution
- Learn preferences pipeline execution
- Project breakdown pipeline execution
- Technique application (category_naming, checkpoint_naming)
- MCP connectivity (Sequential Thinking, In-Memoria)
- Output validation (quality scores, structure)

## Customization

### Add Your Own Documents

```bash
# Add meeting notes
cp your_meeting.md data/docs/meetings/

# Add client emails
cp client_emails.md data/docs/emails/

# Re-index for RAG
sibyl pipeline run --workspace config/workspace.yaml --pipeline index_documents
```

### Adjust Technique Parameters

Edit `config/workspace.yaml`:

```yaml
techniques:
  category_naming:
    config:
      max_categories: 15  # More granular categories

  checkpoint_naming:
    config:
      max_checkpoints: 12  # More milestones
      include_timeline: true
```

### Add Domain-Specific Prompts

Edit `config/pipelines.yaml` to customize prompts for your industry:

```yaml
- name: categorize_items
  params:
    instructions: |
      Organize into categories specific to [YOUR DOMAIN]:
      - Category type 1
      - Category type 2
      ...
```

## Success Metrics

BrightOps uses these metrics to measure impact:

### Time Savings
- **Meeting analysis:** 3 hours → 20 minutes (89% reduction)
- **Preference learning:** 2 weeks → 5 minutes (99% reduction)
- **Proposal writing:** 8 hours → 1 hour (87% reduction)

### Quality Improvements
- **Completeness:** AI catches items humans miss
- **Consistency:** Same structure every time
- **Thoroughness:** More comprehensive than manual work

### Business Impact
- **Proposal velocity:** 3x increase (3/week → 10/week)
- **Client satisfaction:** Higher (communication matches preferences)
- **Team scalability:** New members productive immediately

## Troubleshooting

### MCP Connection Issues

```bash
# Test Sequential Thinking MCP
npx -y @modelcontextprotocol/server-sequential-thinking

# Test In-Memoria MCP
npx -y @modelcontextprotocol/server-memory
```

If npx fails:
- Check Node.js version (needs v16+)
- Check network connectivity
- Try manual npm install

### Pipeline Timeouts

Adjust timeout in `config/workspace.yaml`:
```yaml
connections:
  sequential_thinking:
    timeout_s: 180  # Increase if needed
```

### Low Quality Scores

Review pipeline output:
- Check input document quality (too sparse?)
- Adjust quality criteria in config
- Review validation step errors

### RAG Returns No Results

```bash
# Re-index documents
sibyl pipeline run --workspace config/workspace.yaml --pipeline index_documents

# Check document paths in workspace.yaml
# Verify files exist in data/docs/
```

## Extending This Example

### Add More Scenarios

Create new pipelines in `config/pipelines.yaml`:
- Risk assessment from project docs
- Client onboarding checklist generation
- Technical architecture proposal
- Sprint planning from backlogs

### Integrate with Tools

Connect Sibyl pipelines to:
- Project management (Asana, Jira)
- CRM (Salesforce, HubSpot)
- Communication (Slack, Email)
- Documentation (Notion, Confluence)

### Learn from Actuals

Feed completed project data back:
- Actual vs estimated effort
- Client feedback patterns
- Common risk factors
- Success patterns

## Related Examples

- **Vertex Foundry**: ML platform workflows
- **Northwind Analytics**: Data analysis automation
- **Riverbank Finance**: Compliance and regulatory

## Resources

### Documentation
- [AI Generation Techniques](../../docs/techniques/ai_generation/)
- [Sequential Thinking MCP](../../docs/mcp/sequential_thinking.md)
- [In-Memoria MCP](../../docs/mcp/in_memoria.md)
- [PatternArtifact](../../docs/artifacts/pattern_artifact.md)

### Configuration
- [Workspace Schema](../../docs/config/workspace_schema.md)
- [Pipeline Schema](../../docs/config/pipeline_schema.md)
- [Technique Configuration](../../docs/techniques/configuration.md)

## Contributing

Found a bug? Have a suggestion?
- Open an issue: [GitHub Issues]
- Contribute: [Contributing Guide]

## License

This example is part of the Sibyl project and follows the same license.

---

## Summary

**BrightOps Agency demonstrates:**
- ✓ Unstructured → Structured transformation
- ✓ AI generation techniques (category_naming, checkpoint_naming)
- ✓ Multi-step reasoning (Sequential Thinking MCP)
- ✓ Persistent learning (In-Memoria MCP, PatternArtifact)
- ✓ Real knowledge worker automation
- ✓ Measurable time savings and quality improvements

**This is what Sibyl enables:**
Not just "ask questions about documents", but **systematic transformation of messy inputs into structured, actionable outputs** using composable AI techniques and external reasoning tools.

**Knowledge work automation at its best.**

---

**Questions? Feedback?**
- Example issues: Tag with `example:brightops`
- General questions: [Community Forum]
- Documentation: [Sibyl Docs]

# Scenario 1: Turn Messy Meeting Document into Structured Project Plan

## The Problem

BrightOps just finished a 90-minute client kickoff meeting with Acme Corp. The meeting notes are chaotic:
- Multiple people talking over each other
- Features mentioned without clear prioritization
- Action items buried in discussion
- Tangents and unclear decisions
- Sarah (CEO) wants "everything" but timeline is aggressive
- No clear structure to the requirements

The PM needs to turn this into an actionable project plan BEFORE the next meeting (2 days away). Manually organizing this would take hours of careful reading, note-taking, and structuring.

**This is exactly the kind of "knowledge worker" task Sibyl should automate.**

## What This Scenario Demonstrates

1. **Unstructured → Structured**: Transform messy meeting notes into organized plan
2. **AI Generation Techniques**:
   - `category_naming`: Organize features/tasks into logical categories
   - `checkpoint_naming`: Break work into milestones with dependencies
   - `quality_scoring`: Validate the output meets quality standards
3. **Sequential Thinking MCP**: Multi-step reasoning for analysis and validation
4. **Real-world workflow**: This is what agency PMs actually do after every kickoff

## Prerequisites

- Sequential Thinking MCP installed (see README)
- Meeting document exists at: `data/docs/meetings/kickoff_acme_mobile_2024_03.md`
- Workspace configured with AI generation techniques

## Pipeline Flow

```
Input: Messy meeting notes
  ↓
Step 1: Load meeting document
  ↓
Step 2: Sequential Thinking analyzes meeting content
  └─ Identifies: features, action items, decisions, conflicts
  ↓
Step 3: category_naming technique organizes into categories
  └─ Example categories: "Design", "Development", "QA", "Infrastructure"
  ↓
Step 4: checkpoint_naming creates milestones/checkpoints
  └─ Breaks categories into phased delivery with timeline
  ↓
Step 5: Sequential Thinking validates the plan
  └─ Checks completeness, dependencies, feasibility
  ↓
Step 6: quality_scoring scores the output
  └─ Ensures plan meets quality standards (completeness, clarity, actionability)
  ↓
Step 7: Format final structured plan
  ↓
Output: Structured project plan ready to present
```

## Running the Scenario

### Basic Run

```bash
cd examples/companies/brightops_agency

# Run the meeting_to_plan pipeline
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline meeting_to_plan \
  --input '{"meeting_file": "kickoff_acme_mobile_2024_03.md"}'
```

### With Different Meeting Files

```bash
# Try with the TechStart brainstorm session (even messier)
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline meeting_to_plan \
  --input '{"meeting_file": "brainstorm_techstart_website_2024_04.md"}'

# Or the status update meeting
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline meeting_to_plan \
  --input '{"meeting_file": "status_update_globex_q2_2024.md"}'
```

### Expected Output

The pipeline produces a structured plan with:

#### Categories
```markdown
## Work Stream Categories

### Design & UX
- Mobile app UI/UX design
- Design system creation
- User flow mapping
- Prototype development
- Accessibility compliance

### Frontend Development
- iOS app development (Swift/SwiftUI)
- Android app development (Kotlin)
- Cross-platform considerations
- Dark mode implementation
- Push notification handling

### Backend & Integration
- REST API development
- Oracle database integration
- Authentication system (JWT)
- Payment integration (Stripe)
- Loyalty program backend

### Quality Assurance
- Testing strategy
- iOS/Android testing
- API integration testing
- App Store submission testing
- Performance testing

### Infrastructure & DevOps
- CI/CD pipeline
- Staging environment
- Production deployment
- Monitoring and alerting
- App Store/Play Store setup
```

#### Checkpoints/Milestones
```markdown
## Delivery Milestones

### Milestone 1: Discovery & Design (Weeks 1-4)
**Deliverables:**
- Finalized requirements document
- UI/UX designs and prototypes
- Technical architecture document
- API specification
**Dependencies:** None
**Team:** PM, Designer, Lead Dev

### Milestone 2: MVP Development (Weeks 5-10)
**Deliverables:**
- Core reservation booking flow
- User authentication
- Restaurant discovery
- Basic loyalty program
**Dependencies:** Milestone 1 complete, Oracle API available
**Team:** Full team

### Milestone 3: Testing & Refinement (Weeks 11-13)
**Deliverables:**
- Complete test coverage
- Bug fixes
- Performance optimization
- iOS/Android parity
**Dependencies:** Milestone 2 complete
**Team:** QA, Developers

### Milestone 4: Launch Preparation (Weeks 14-16)
**Deliverables:**
- App Store submissions
- Production deployment
- Monitoring setup
- Launch day support
**Dependencies:** Milestone 3 complete, App Store approval
**Team:** Full team
```

#### Validation Notes
```markdown
## Validation & Risks

**Completeness Check:** ✓
- All features from meeting captured
- Action items identified
- Timeline realistic (16 weeks)

**Key Risks Identified:**
- Oracle API integration (external dependency)
- App Store approval (previous rejection history)
- Aggressive timeline (June 30 target)
- Scope creep potential (Sarah mentioned 20+ features)

**Recommendations:**
1. Start API integration work immediately (don't wait for their team)
2. Mock API for parallel development
3. Phase 1 vs Phase 2 feature distinction critical
4. Weekly check-ins with client to manage expectations
```

#### Quality Score
```markdown
## Quality Assessment

**Overall Score:** 8.5/10

**Completeness:** 9/10
- All major features identified
- Action items extracted
- Timeline accounted for

**Clarity:** 8/10
- Categories well-defined
- Milestones clear
- Some ambiguity on Phase 2 scope

**Actionability:** 9/10
- Next steps are clear
- Owners can be assigned
- Dependencies identified

**Timeline Realism:** 7/10
- Aggressive but feasible
- Requires no delays
- Buffer time minimal
```

## What Gets Automated

Without Sibyl:
- PM reads 90-minute meeting notes (30 minutes)
- Manually extracts features and requirements (45 minutes)
- Organizes into categories (30 minutes)
- Creates milestone breakdown (45 minutes)
- Reviews for completeness and conflicts (30 minutes)
- Formats into presentable document (30 minutes)
- **Total: ~3 hours of manual work**

With Sibyl:
- Run pipeline (3 minutes)
- Review and refine output (15 minutes)
- **Total: ~20 minutes**

**Time saved: 2.5 hours per kickoff meeting**

## Key Techniques Showcased

### category_naming
- **What it does:** Organizes unstructured items into logical categories
- **Why it matters:** Meetings produce scattered ideas; categories enable parallel workstreams
- **How it's used:** Takes feature list, returns categorized work structure

### checkpoint_naming
- **What it does:** Breaks project into phased milestones with dependencies
- **Why it matters:** Clients need timelines; checkpoints enable progress tracking
- **How it's used:** Takes categories, returns milestone plan with timeline

### Sequential Thinking MCP
- **What it does:** Step-by-step reasoning and validation
- **Why it matters:** Complex analysis requires multi-step logic, not single prompt
- **How it's used:**
  - Initial analysis: Extract features, action items, decisions
  - Validation: Check plan completeness and feasibility

### quality_scoring
- **What it does:** Scores output against quality criteria
- **Why it matters:** Ensures automated output meets professional standards
- **How it's used:** Validates final plan before human review

## Variations to Try

### Different Meeting Types
```bash
# Brainstorm session (very unstructured)
--input '{"meeting_file": "brainstorm_techstart_website_2024_04.md"}'

# Status update (different structure)
--input '{"meeting_file": "status_update_globex_q2_2024.md"}'

# Retrospective (lessons learned)
--input '{"meeting_file": "retrospective_fintech_project_2024_03.md"}'

# Discovery session (Q&A format)
--input '{"meeting_file": "discovery_healthtech_2024_05.md"}'
```

### Adjust Pipeline Parameters
Modify `config/pipelines.yaml`:

```yaml
# More categories (granular breakdown)
category_naming:
  config:
    max_categories: 15

# Shorter timeline checkpoints
checkpoint_naming:
  config:
    max_checkpoints: 12
    timeline_weeks: 12

# Stricter quality standards
quality_scoring:
  config:
    min_score: 0.8
```

## Success Criteria

Pipeline succeeds if:
- ✓ All major features from meeting are captured
- ✓ Categories are logical and parallelizable
- ✓ Checkpoints have clear deliverables
- ✓ Timeline is realistic
- ✓ Dependencies are identified
- ✓ Quality score > 7.0/10
- ✓ Output is ready to present to client

## Next Steps

After running this scenario:

1. **Try Scenario 2:** Learn client preferences from emails
2. **Customize categories:** Edit technique config for your domain
3. **Add your own meetings:** Drop meeting notes in `data/docs/meetings/`
4. **Chain with other workflows:** Use output as input to project tracking tools

## Troubleshooting

**Pipeline times out:**
- Reduce `timeout_s` in workspace.yaml
- Simplify the meeting document
- Check Sequential Thinking MCP is running

**Categories are too generic:**
- Adjust `max_categories` in technique config
- Provide domain-specific examples in prompts
- Try different meeting documents

**Quality score is low:**
- Review the validation step output
- Check if meeting notes are too sparse
- Adjust quality criteria in config

## Real-World Impact

This scenario demonstrates a **repeatable workflow** for any agency:
- Every client kickoff meeting
- Every brainstorm session
- Every status update that needs structuring

The AI generation techniques (`category_naming`, `checkpoint_naming`) are the key:
- **Not just summarization** (GPT could do that)
- **Structured transformation** using domain-specific techniques
- **Validated output** with quality scoring

This is the future of knowledge work: **humans in the loop, AI doing the heavy lifting.**

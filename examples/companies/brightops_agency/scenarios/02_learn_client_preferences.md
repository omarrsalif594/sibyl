# Scenario 2: Learn Client Communication Preferences Over Time

## The Problem

BrightOps works with multiple clients, each with different communication styles and preferences:
- **Sarah (Acme CEO):** Fast decisions, brief updates, action-oriented
- **Marcus (TechStart Director):** Detailed feedback, formal process, thorough documentation
- **Rachel (Globex CTO):** Technical depth, code-level discussions, high standards

Team members keep re-learning these preferences the hard way:
- Priya sends detailed design rationale → Sarah says "too much, give me 3 bullet points"
- Alex sends brief technical update → Marcus asks for comprehensive documentation
- New team members don't know client preferences at all

**This knowledge should be captured, learned, and retrievable.**

## What This Scenario Demonstrates

1. **Pattern Learning**: Extract communication patterns from historical emails
2. **RAG Pipeline**: Vector search over client communication history
3. **In-Memoria MCP**: Store patterns as graph entities for retrieval
4. **PatternArtifact**: Typed artifact for client preferences
5. **Memory Across Projects**: Learn once, use forever

## Prerequisites

- In-Memoria MCP installed (see README)
- Client email documents in: `data/docs/emails/`
- Vector store configured for RAG
- Documents indexed (run `index_documents` pipeline first)

## Pipeline Flow

```
Input: Client name (e.g., "Acme CEO Sarah")
  ↓
Step 1: RAG over client emails
  └─ Semantic search for communication patterns
  ↓
Step 2: Sequential Thinking analyzes patterns
  └─ Communication style, preferences, decision-making
  ↓
Step 3: Store in In-Memoria as graph entity
  └─ Client entity with pattern observations
  ↓
Step 4: Create pattern relations
  └─ Links: client → communication_style, decision_making
  ↓
Step 5: Convert to PatternArtifact
  └─ Typed, structured pattern data
  ↓
Step 6: Summarize for humans
  └─ Markdown summary of key preferences
  ↓
Output: PatternArtifact + human-readable summary
```

## Running the Scenario

### First: Index Documents for RAG

```bash
cd examples/companies/brightops_agency

# Index all documents (run once, or when documents change)
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline index_documents
```

### Learn Preferences for Each Client

```bash
# Learn Sarah (Acme CEO) preferences
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline learn_preferences \
  --input '{"client_name": "Acme CEO Sarah"}'

# Learn Marcus (TechStart) preferences
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline learn_preferences \
  --input '{"client_name": "TechStart Marcus"}'

# Learn Rachel (Globex CTO) preferences
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline learn_preferences \
  --input '{"client_name": "Globex CTO Rachel"}'
```

### Expected Output

#### For Sarah (Acme CEO)

```markdown
# Client Communication Patterns: Acme CEO Sarah

## Pattern Artifact
**Pattern Name:** acme_ceo_sarah_communication_patterns
**Category:** communication
**Confidence:** 0.85
**Provider:** in_memoria

## Communication Style
- **Brevity:** Prefers bullet points over long emails
- **Speed:** Makes decisions quickly, values momentum
- **Tone:** Direct and casual, not formal
- **Format:** "Three bullet points, not a dissertation"

**Example:**
> "Quick feedback: LOVE / CONCERNS / Can you send v2 by end of week?"

## Response Expectations
- **Urgency:** Expects 24-hour response for email, 2 hours for urgent text
- **Status Updates:** Weekly, brief, executive-level only
- **Escalation:** Flags blockers she can help with
- **No Need:** Technical details (Mike handles those)

**Example:**
> "What I need to know: Are we on track? (Yes/No/At Risk) Any blockers I need to help with?"

## Decision-Making Style
- **Fast Decisions:** Doesn't overthink, values speed over perfection
- **Trusts Expertise:** "Don't overthink it. Speed > perfection"
- **Context:** Board pressure, competitive urgency
- **Delegation:** Trusts team to make most decisions

**Example:**
> "Go with Stripe. Don't overthink it."

## Meeting Preferences
- **Duration:** Keep meetings short (30 min max)
- **Agenda:** Send in advance
- **Action Items:** Follow-up email with clear owners
- **Availability:** Includes phone number for urgent issues

## Budget Sensitivity
- **Willing to Spend:** If it supports timeline goals
- **Needs Clarity:** Requires quick turnaround on budget decisions
- **Trade-offs:** Timeline > Features > Budget

**Example:**
> "Can you deliver loyalty program AND hit June 30? If yes: approved. If no: phase 2."

## Feedback Style
- **Positive:** Gives specific, generous praise
- **Constructive:** Direct but not harsh
- **Recognition:** Remembers who did what, credits individuals

**Example:**
> "Alex: The real-time availability is so fast. Whatever you did to optimize it, it worked."

## Work-Life Boundaries
- **Late Emails:** Sends late but says "ignore until morning"
- **Respects Time:** Doesn't expect 24/7 availability
- **Human:** Acknowledges we all have lives outside work

## How to Work With Sarah

**DO:**
- Keep emails brief and action-oriented
- Flag urgent items clearly
- Celebrate wins (she appreciates it)
- Present 2-3 options with your recommendation
- Always CC Jennifer on major discussions

**DON'T:**
- Send long technical explanations (she won't read them)
- Wait to escalate problems
- Sugarcoat bad news
- Assume she needs to approve small decisions

**Optimal Email Format:**
```
Subject: [STATUS] Project Name - Week X

Are we on track? YES / AT RISK

Blockers needing your help:
- Budget approval for Feature X ($Y)
- Introduction to Restaurant Partner contact

What's shipping this week:
- Feature A
- Feature B

—Team
```

## Confidence Score: 85%
**Based on:** 10 email threads, 6 months of communication
**High confidence patterns:**
- Preference for brevity (100% consistent)
- Fast decision-making (95% consistent)
- Generous with specific praise (90% consistent)

**Medium confidence patterns:**
- Budget flexibility (varies by context)
- Technical detail tolerance (delegates to Mike)
```

#### For Marcus (TechStart)

```markdown
# Client Communication Patterns: TechStart Marcus

## Pattern Artifact
**Pattern Name:** techstart_marcus_communication_patterns
**Category:** communication
**Confidence:** 0.88
**Provider:** in_memoria

## Communication Style
- **Formality:** Professional, structured, includes full signature
- **Detail:** Wants comprehensive information and documentation
- **Process-Oriented:** Clear workflows, defined approval chains
- **Thoroughness:** Reviews carefully, asks detailed questions

**Example:**
> "Dear Jennifer, I hope this email finds you well..." (formal opening every time)

## Feedback Style
- **Structured:** Organizes feedback by category
- **Balanced:** Lists strengths AND concerns for every option
- **Specific:** "Section 3.2 mentions '8-10 weeks' - can you provide precise estimate?"
- **Appreciative:** Always acknowledges good work

**Example:**
```
CONCEPT A (Modern Minimalist):

Strengths:
- Clean professional aesthetic
- Good use of whitespace

Concerns:
- May be too minimal
- Missing social proof
```

## Decision-Making Style
- **Deliberate:** Takes time to evaluate options thoroughly
- **Question-Heavy:** Asks detailed clarifying questions
- **Collaborative:** Wants input from stakeholders
- **Risk-Aware:** Identifies and plans for risks upfront

**Example:**
> "I have several questions and clarifications needed: TIMELINE / TECHNICAL APPROACH / CONTENT MIGRATION..."

## Meeting Preferences
- **Structured:** Same agenda every time, predictable format
- **Scheduled:** Prefers planned meetings over ad-hoc calls
- **Documentation:** Wants written follow-up after every meeting
- **Stakeholder Mapping:** Clear roles and approval process

**Example:**
> "Please allow 3-5 business days for each review cycle. If urgent, flag it."

## Process Expectations
- **Review Cycles:** Multi-stage with defined stakeholders
- **Feedback Format:** Wants written feedback documents
- **Sign-off:** Requires formal approval from multiple people
- **Timeline:** Plans around his availability (flags when traveling)

## QA & Testing
- **Thorough:** Wants comprehensive testing plan
- **Launch Criteria:** Clear, documented checklist
- **Risk Mitigation:** Asks about backup plans and rollback procedures
- **Pre-launch:** Gets nervous, needs reassurance with data

**Example:**
> "Before we can launch, we need: Zero critical bugs, All P1 features complete, Performance benchmarks met..."

## How to Work With Marcus

**DO:**
- Provide detailed, organized documentation
- Anticipate questions with thorough proposals
- Follow structured processes
- Allow time for review cycles (3-5 business days)
- CC all stakeholders clearly
- Send meeting agendas in advance

**DON'T:**
- Rush decisions
- Skip documentation
- Assume informal communication is sufficient
- Surprise him with last-minute asks

**Optimal Email Format:**
```
Subject: [TOPIC] - Structured Proposal

Dear Marcus,

[Opening paragraph with context]

SECTION 1: TOPIC A
- Detailed point
- Detailed point

SECTION 2: TOPIC B
- Detailed point
- Detailed point

QUESTIONS FOR YOU:
1. Specific question
2. Specific question

NEXT STEPS:
- Action item with owner and date

Best regards,
[Full signature]
```

## Post-Engagement
- **Gratitude:** Sends thoughtful thank-you notes
- **Metrics:** Provides specific success data
- **Referrals:** Actively refers to other potential clients
- **Long-term:** Thinks about future engagements

**Example:**
> "METRICS (first 2 weeks): 12,000 visitors (up 3x), 45% increase in applications..."

## Confidence Score: 88%
**Based on:** 10 email threads, 4 months of engagement
**High confidence patterns:**
- Formal communication style (100% consistent)
- Detail-oriented (95% consistent)
- Process adherence (90% consistent)

**Medium confidence patterns:**
- Anxiety level pre-launch (varies by project phase)
```

## What Gets Stored in In-Memoria

The pipeline stores client patterns as **graph entities** that persist across sessions:

```
[Client: "Acme CEO Sarah"]
  ├─ prefers → [communication_style: "brief_action_oriented"]
  ├─ exhibits → [decision_making: "fast_trusts_expertise"]
  ├─ requires → [update_format: "bullet_points_executive_level"]
  └─ values → [traits: "speed_momentum_results"]

[Client: "TechStart Marcus"]
  ├─ prefers → [communication_style: "formal_detailed_structured"]
  ├─ exhibits → [decision_making: "deliberate_collaborative_thorough"]
  ├─ requires → [update_format: "comprehensive_documentation"]
  └─ values → [traits: "process_quality_thoroughness"]
```

## Using Learned Patterns

### Retrieve Patterns Later

```bash
# Query In-Memoria for client preferences
sibyl mcp call \
  --provider in_memoria \
  --tool search_nodes \
  --params '{"query": "Acme CEO Sarah communication preferences"}'

# Or open specific client entity
sibyl mcp call \
  --provider in_memoria \
  --tool open_nodes \
  --params '{"names": ["Acme CEO Sarah"]}'
```

### Apply to New Team Members

New developer joining Acme project:
1. Retrieve Sarah's PatternArtifact
2. Share summary: "Here's how to work with Sarah"
3. No learning curve, immediate effectiveness

### Personalize Future Communication

Before sending email to Marcus:
1. Check his preference: detailed, structured
2. Format accordingly
3. Higher client satisfaction

## Key Techniques Showcased

### RAG Pipeline
- **Semantic search** over historical emails
- Finds relevant communication examples
- Context for pattern analysis

### Sequential Thinking MCP
- **Multi-step analysis** of communication patterns
- Identifies: style, preferences, decision-making, expectations
- More nuanced than single-shot LLM call

### In-Memoria MCP
- **Persistent memory** across sessions
- Graph structure for relationships
- Queryable pattern knowledge base

### PatternArtifact
- **Typed artifact** from `sibyl.core.artifacts`
- Structured pattern data with confidence scores
- Standardized format for client preferences

## Real-World Impact

### Time Saved
- Learning client preferences: 2-3 weeks → 5 minutes
- Onboarding new team members: 1 week → 1 hour
- Reformatting communications: 30 min/email → 0 min

### Quality Improved
- Client satisfaction: Higher (communication matches preferences)
- Team confidence: Higher (know what clients expect)
- Misunderstandings: Fewer (explicit preferences documented)

### Scalability
- Works with 5 clients or 50 clients
- Patterns accumulate over time
- Institutional knowledge captured

## Variations to Try

### Learn Different Pattern Types

```bash
# Technical preferences (for CTOs)
--input '{"client_name": "Globex CTO Rachel", "pattern_type": "technical"}'

# Budget sensitivity patterns
--input '{"client_name": "Acme CEO Sarah", "pattern_type": "budget"}'

# Decision-making timelines
--input '{"client_name": "TechStart Marcus", "pattern_type": "decision_speed"}'
```

### Cross-Client Pattern Analysis

```bash
# Find common patterns across all CEOs
sibyl mcp call \
  --provider in_memoria \
  --tool search_nodes \
  --params '{"query": "CEO communication patterns common traits"}'
```

## Success Criteria

Pipeline succeeds if:
- ✓ Patterns extracted from email history
- ✓ PatternArtifact created with confidence score
- ✓ Patterns stored in In-Memoria graph
- ✓ Summary is actionable for team members
- ✓ Patterns are retrievable later
- ✓ New team members can query and use

## Troubleshooting

**No emails found:**
- Check document indexing (run `index_documents` first)
- Verify client name matches email content
- Try broader query terms

**Low confidence scores:**
- Need more email examples (< 5 emails = low confidence)
- Patterns are inconsistent (client changes style)
- Email content lacks preference signals

**In-Memoria connection fails:**
- Check MCP server is running
- Verify transport configuration
- Test with simple `search_nodes` call first

## Next Steps

After running this scenario:

1. **Add more clients:** Drop email threads in `data/docs/emails/`
2. **Query patterns:** Use In-Memoria to retrieve learned preferences
3. **Generate templates:** Create email templates per client type
4. **Train team:** Share PatternArtifacts with new team members
5. **Iterate:** Patterns improve as more emails are processed

## The Big Idea

This scenario demonstrates **organizational learning**:
- Knowledge isn't trapped in people's heads
- Patterns are explicit, queryable, improvable
- New team members get institutional knowledge immediately
- Client relationships improve through personalization

**This is what makes Sibyl different from "just LLM + RAG":**
- Structured pattern extraction (not just search)
- Persistent memory (In-Memoria MCP)
- Typed artifacts (PatternArtifact)
- Confidence scoring
- Cross-session learning

The future of knowledge work is **systems that learn and remember.**

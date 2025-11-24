# Scenario 3: Generate Project Breakdown from One-Liner

## The Problem

A potential client reaches out with a brief project idea:

> "Build a mobile app for restaurant reservations"

Or:

> "We need a patient portal for our healthcare network"

The sales team needs to respond quickly with:
- Detailed project scope
- Work breakdown structure
- Timeline estimate
- Budget estimate
- Risk assessment

Manually creating this from scratch takes a PM 4-8 hours. Often involves:
- Researching similar projects
- Breaking down into phases
- Estimating each component
- Identifying dependencies
- Documenting assumptions

**This should be automated, with AI expanding scope intelligently.**

## What This Scenario Demonstrates

1. **Scope Expansion**: One-liner → comprehensive project breakdown
2. **Sequential Thinking MCP**: Multi-step reasoning to explore scope, architecture, trade-offs
3. **AI Generation Techniques**:
   - `category_naming`: Organize work into parallelizable streams
   - `checkpoint_naming`: Create phased delivery plan
4. **Estimation**: Effort, timeline, budget, team composition
5. **Real Proposal Generation**: Output is client-ready document

## Prerequisites

- Sequential Thinking MCP installed
- AI generation techniques configured
- Understanding of typical project structure

## Pipeline Flow

```
Input: Brief project description + timeline
  ↓
Step 1: Sequential Thinking expands scope
  └─ Core features, user flows, technical architecture
  ↓
Step 2: Sequential Thinking explores architecture options
  └─ Frontend, backend, database, hosting, API design
  ↓
Step 3: category_naming organizes into work streams
  └─ Design, Frontend, Backend, QA, DevOps, etc.
  ↓
Step 4: checkpoint_naming creates phased milestones
  └─ MVP → Enhanced Features → Polish → Launch
  ↓
Step 5: Sequential Thinking estimates effort
  └─ Person-weeks, timeline, team size, budget
  ↓
Step 6: quality_scoring validates breakdown
  └─ Completeness, feasibility, clarity, client value
  ↓
Step 7: Generate final project breakdown document
  ↓
Output: Comprehensive project breakdown (ready for proposal)
```

## Running the Scenario

### Basic Examples

```bash
cd examples/companies/brightops_agency

# Restaurant reservation app
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "Build a mobile app for restaurant reservations",
    "timeline_weeks": 16
  }'

# Patient portal
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "Healthcare patient portal with appointment booking and test results",
    "timeline_weeks": 20
  }'

# E-commerce platform
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "E-commerce platform for selling handmade crafts",
    "timeline_weeks": 12
  }'

# Fitness class booking
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "Platform for booking fitness classes across multiple gyms",
    "timeline_weeks": 14
  }'
```

### Advanced: With Additional Context

```bash
# Include budget constraint
sibyl pipeline run \
  --workspace config/workspace.yaml \
  --pipeline project_breakdown \
  --input '{
    "project_brief": "Real estate listing platform with virtual tours",
    "timeline_weeks": 18,
    "budget_usd": 150000,
    "team_size": 5
  }'
```

## Expected Output

### Example: Restaurant Reservation App

```markdown
# Project Breakdown: Restaurant Reservation Mobile App

## Executive Summary

### Project Vision
A modern mobile application enabling users to discover restaurants, book reservations in real-time, manage dining preferences, and earn loyalty rewards. The platform will serve urban professionals aged 25-45 and compete with established players like OpenTable and Resy.

### Core Value Proposition
- **For Users:** Seamless booking experience, personalized recommendations, loyalty rewards
- **For Restaurants:** Reduced phone call volume, better table utilization, customer insights
- **For Business:** Revenue through booking fees and premium restaurant placements

### Key Constraints
- Timeline: 16 weeks to MVP launch
- Platforms: iOS and Android (native or cross-platform)
- Integration: Must work with existing POS/reservation systems

---

## Technical Architecture

### Frontend Options Evaluated

**Option A: React Native**
- Pros: Single codebase, fast development, good ecosystem
- Cons: Performance limitations for complex animations
- Recommendation: ✓ Best for timeline and budget

**Option B: Native (Swift + Kotlin)**
- Pros: Best performance, full platform features
- Cons: 2x development time, separate codebases
- Recommendation: Consider for v2

**Option C: Flutter**
- Pros: Fast rendering, single codebase, growing ecosystem
- Cons: Team ramp-up time, smaller community
- Recommendation: If team has Dart experience

### Backend Architecture
- **API:** REST API (Node.js + Express or Python + FastAPI)
- **Database:** PostgreSQL (relational data, complex queries)
- **Caching:** Redis (real-time availability, session management)
- **Search:** Elasticsearch (restaurant discovery with fuzzy matching)
- **File Storage:** S3 (restaurant photos, user profiles)

### Integration Points
- Restaurant POS systems (via API or webhook)
- Payment gateway (Stripe recommended)
- Push notifications (FCM + APNS)
- SMS service (Twilio for confirmations)
- Email service (SendGrid for notifications)
- Maps API (Google Maps or Mapbox)

### Hosting & DevOps
- **Cloud:** AWS (EC2/ECS + RDS + S3)
- **CI/CD:** GitHub Actions
- **Monitoring:** DataDog or New Relic
- **Error Tracking:** Sentry

---

## Work Stream Categories

### 1. Product & Design (3-4 weeks)
**Scope:**
- User research and competitive analysis
- User flows and journey mapping
- Wireframes and interactive prototypes
- Visual design and brand identity
- Design system creation
- Accessibility audit (WCAG 2.1 AA)

**Team:** Product Manager, UX/UI Designer
**Deliverables:**
- Requirements document
- User flow diagrams
- High-fidelity mockups
- Design system (Figma)
- Prototype for user testing

---

### 2. Mobile Development (8-10 weeks)
**Scope:**
- App architecture and project setup
- User authentication (email, social login)
- Restaurant discovery and search
- Booking flow with real-time availability
- User profile and preferences
- Reservation management
- Push notifications
- Loyalty program UI
- Payment integration
- Map integration
- Offline capability for viewing reservations

**Team:** 2 Mobile Developers (React Native or iOS/Android)
**Key Technical Challenges:**
- Real-time availability sync
- Optimistic UI updates
- Handling network failures gracefully
- Payment security

**Deliverables:**
- iOS app (TestFlight beta)
- Android app (Play Store beta)
- Unit and integration tests

---

### 3. Backend Development (8-10 weeks, parallel with mobile)
**Scope:**
- API design and documentation (OpenAPI)
- User authentication and authorization (JWT)
- Restaurant data models and endpoints
- Booking engine with conflict resolution
- Real-time availability calculation
- Loyalty program backend
- Payment processing
- Notification system (push, email, SMS)
- Admin dashboard for restaurants
- Analytics and reporting
- Database schema and migrations
- Integration with POS systems

**Team:** 2 Backend Developers
**Key Technical Challenges:**
- Preventing double-bookings (race conditions)
- Handling peak load (dinner time rush)
- Data consistency across systems
- Webhook reliability

**Deliverables:**
- REST API (documented with Swagger)
- Admin dashboard
- Database schema
- Integration adapters
- API test suite

---

### 4. Quality Assurance (4-5 weeks, ongoing)
**Scope:**
- Test strategy and plan
- Manual testing (functional, UI/UX)
- Automated testing setup
- Performance testing (load, stress)
- Security testing (OWASP Mobile Top 10)
- Accessibility testing
- Cross-device testing
- App Store submission testing
- Beta user testing

**Team:** QA Engineer (full-time from week 4)
**Key Focus Areas:**
- Booking flow integrity
- Payment security
- Notification delivery
- Offline behavior
- Edge cases and error handling

**Deliverables:**
- Test cases and scenarios
- Bug reports and fixes
- Performance benchmarks
- Security audit report

---

### 5. DevOps & Infrastructure (2-3 weeks, ongoing)
**Scope:**
- AWS account setup and configuration
- CI/CD pipeline (build, test, deploy)
- Environment setup (dev, staging, prod)
- Database provisioning and backups
- Monitoring and alerting
- Log aggregation
- SSL certificates
- App Store/Play Store setup
- Deployment automation

**Team:** DevOps Engineer (part-time or consultant)
**Key Focus Areas:**
- Zero-downtime deployments
- Disaster recovery plan
- Auto-scaling configuration
- Cost optimization

**Deliverables:**
- Production infrastructure
- CI/CD pipeline
- Monitoring dashboards
- Deployment runbooks

---

## Delivery Milestones

### Phase 1: Discovery & Foundation (Weeks 1-4)
**Goal:** Validate scope, design user experience, establish technical foundation

**Deliverables:**
- Finalized requirements document
- Technical architecture document
- API specification
- High-fidelity designs and prototype
- Development environment setup

**Team:** PM, Designer, Lead Developer
**Exit Criteria:**
- Client approves designs
- Technical approach validated
- Team has clear requirements

**Risks:**
- Scope creep during discovery
- Client availability for feedback

---

### Phase 2: MVP Development (Weeks 5-11)
**Goal:** Build core booking flow, integrate with restaurants

**Key Features:**
- User authentication
- Restaurant discovery (search, filter, map)
- Real-time booking flow
- Reservation management
- Push notifications
- Basic loyalty program
- Payment integration

**Team:** Full team (PM, Designer, 2 Mobile Devs, 2 Backend Devs, QA part-time)
**Exit Criteria:**
- Core booking flow works end-to-end
- Integration with 10 test restaurants
- Performance meets benchmarks
- No P0 bugs

**Risks:**
- POS integration delays
- Real-time availability complexity
- Payment gateway approval time

---

### Phase 3: Testing & Refinement (Weeks 12-14)
**Goal:** Ensure quality, fix bugs, optimize performance

**Activities:**
- Comprehensive testing (functional, performance, security)
- Bug fixes and polish
- Performance optimization
- Accessibility improvements
- Beta testing with real users (25-50 users)
- Incorporate feedback

**Team:** Full team with focus on QA
**Exit Criteria:**
- Zero P0/P1 bugs
- Performance benchmarks met (load time < 3s)
- Accessibility score > 85
- Positive beta user feedback

**Risks:**
- Unexpected bugs in complex scenarios
- Performance issues at scale

---

### Phase 4: Launch Preparation (Weeks 15-16)
**Goal:** Submit to app stores, prepare for launch

**Activities:**
- App Store and Play Store submissions
- Marketing assets (screenshots, descriptions)
- Privacy policy and terms of service
- Launch communication plan
- Support documentation
- Monitoring and alerting setup
- Launch day runbook

**Team:** Full team
**Exit Criteria:**
- Apps approved by Apple and Google
- Production infrastructure stable
- Support team trained
- Launch plan finalized

**Risks:**
- App Store rejection (submit early!)
- Last-minute critical bugs

---

## Effort & Timeline Estimates

### Development Effort (Person-Weeks)

| Category | Effort | Percentage |
|----------|--------|------------|
| Product & Design | 12 weeks | 15% |
| Mobile Development | 20 weeks | 25% |
| Backend Development | 20 weeks | 25% |
| Quality Assurance | 12 weeks | 15% |
| DevOps | 8 weeks | 10% |
| Project Management | 8 weeks | 10% |
| **Total** | **80 person-weeks** | **100%** |

### Timeline: 16 Weeks (Aggressive but Feasible)

**Assumptions:**
- Team of 6-7 people working in parallel
- Mobile and backend development overlap
- QA starts at week 4, continues through launch
- No major scope changes after week 2
- Client feedback turnaround < 48 hours
- No extended POS integration delays

**Critical Path:**
1. Weeks 1-4: Design and architecture (blocking)
2. Weeks 5-11: MVP development (mobile + backend in parallel)
3. Weeks 12-14: Testing and refinement
4. Weeks 15-16: App Store submission and launch prep

**Buffer:** Minimal (2 weeks within 16-week timeline)

**Risk Mitigation:**
- Start POS integration early with mocks
- Submit to App Store at week 14 (allow 2 weeks for review)
- Weekly client check-ins to avoid surprises
- Daily standups to catch blockers fast

---

### Team Composition

**Core Team (Weeks 1-16):**
- 1 Project Manager (full-time)
- 1 Product Designer (full-time weeks 1-6, part-time weeks 7-16)
- 2 Mobile Developers (full-time)
- 2 Backend Developers (full-time)
- 1 QA Engineer (full-time from week 4)
- 1 DevOps Engineer (part-time, ~15 hours/week)

**Total Team:** 7-8 people (FTE: ~6.5)

---

### Budget Estimate

**Hourly Rates (Average):**
- Project Manager: $150/hour
- Designer: $140/hour
- Senior Developer: $160/hour
- QA Engineer: $120/hour
- DevOps Engineer: $140/hour

**Labor Costs:**
| Role | Hours | Rate | Total |
|------|-------|------|-------|
| Project Manager | 640 | $150 | $96,000 |
| Designer | 400 | $140 | $56,000 |
| Mobile Developers (2) | 1,280 | $160 | $204,800 |
| Backend Developers (2) | 1,280 | $160 | $204,800 |
| QA Engineer | 480 | $120 | $57,600 |
| DevOps Engineer | 240 | $140 | $33,600 |
| **Subtotal Labor** | | | **$652,800** |

**Infrastructure & Tools (16 weeks):**
- AWS hosting (dev + staging + prod): $3,000
- Development tools (Figma, GitHub, etc.): $1,500
- Third-party APIs (Maps, SMS, Email): $2,000
- App Store fees (Apple + Google): $200
- **Subtotal Infrastructure:** **$6,700**

**Contingency (10%):** $65,950

**Total Estimated Budget:** **$725,450**

**Scaled Options:**
- **Budget Option ($180,000):** Reduce to MVP only, 3-person team, 20 weeks
- **Mid-Tier Option ($400,000):** Optimize team size, extend timeline to 20 weeks
- **Full Option ($725,000):** As described above, 16-week aggressive timeline

---

## Risk Assessment

### Technical Risks (Medium-High)

**Risk 1: POS Integration Complexity**
- Impact: High (core feature)
- Probability: Medium
- Mitigation: Start with mock API, work with 2-3 early partner restaurants

**Risk 2: Real-Time Availability Sync**
- Impact: High (user experience)
- Probability: Medium
- Mitigation: Use event-driven architecture, extensive testing, fallback UI

**Risk 3: App Store Approval**
- Impact: High (can delay launch)
- Probability: Low-Medium
- Mitigation: Submit early (week 14), follow guidelines meticulously, have appeal plan

**Risk 4: Payment Security**
- Impact: Critical (legal/compliance)
- Probability: Low
- Mitigation: Use Stripe (PCI-compliant), security audit, penetration testing

### Schedule Risks (Medium)

**Risk 5: Scope Creep**
- Impact: High (timeline/budget)
- Probability: High
- Mitigation: Strict phase 1 vs phase 2 distinction, change request process

**Risk 6: Client Availability**
- Impact: Medium (feedback delays)
- Probability: Medium
- Mitigation: Set expectations upfront, weekly check-ins, async feedback tools

**Risk 7: Team Availability**
- Impact: Medium
- Probability: Low
- Mitigation: Backup developers identified, knowledge sharing, documentation

### Business Risks (Low-Medium)

**Risk 8: Market Competition**
- Impact: Medium (product differentiation)
- Probability: High
- Mitigation: Focus on loyalty program USP, localized experience

**Risk 9: Restaurant Adoption**
- Impact: High (network effects)
- Probability: Medium
- Mitigation: Early partner recruitment, value proposition for restaurants

---

## Quality Assessment

**Overall Score:** 8.7/10

**Completeness:** 9/10
- All major components identified
- Architecture well-thought-out
- Clear deliverables and milestones

**Clarity:** 9/10
- Work breakdown is specific
- Timeline is realistic
- Roles and responsibilities clear

**Feasibility:** 8/10
- Aggressive timeline requires disciplined execution
- Budget is realistic for scope
- Team composition appropriate

**Client Value:** 9/10
- Addresses core business needs
- Phased delivery allows early feedback
- Clear ROI path

**Areas for Improvement:**
- Contingency time is minimal (risk)
- Dependency on third-party integrations (POS)
- Marketing and go-to-market strategy not covered

---

## Assumptions & Exclusions

### Assumptions
- Client provides restaurant partner contacts for integration testing
- Restaurant POS systems have usable APIs
- Client can review and approve designs within 48 hours
- Payment gateway approval takes < 1 week
- App Store review takes < 2 weeks

### Explicitly Out of Scope (Phase 2)
- Restaurant reviews and ratings
- Social sharing features
- Wait list management
- Group reservations
- Dietary preference filtering
- Multi-language support
- Web application (mobile only for Phase 1)
- Advanced analytics dashboard

---

## Next Steps

### For Client Decision
1. Review and approve scope
2. Confirm budget availability
3. Identify key stakeholders and decision-makers
4. Provide restaurant partner contacts for early integration

### For BrightOps Team
1. Conduct technical discovery with client's existing systems
2. Draft detailed requirements document
3. Create project plan with Gantt chart
4. Assemble team and confirm availability
5. Schedule kickoff meeting

### Immediate Actions (Upon Approval)
- Week 1: Kickoff, requirements finalization
- Week 2: Technical architecture deep-dive, POS API evaluation
- Week 3: Design sprint, user flows
- Week 4: Development begins

---

**Document Status:** Draft for Client Review
**Prepared By:** BrightOps Agency - Jennifer (PM)
**Date:** [Current Date]
**Valid Until:** [30 days]
```

## What Gets Automated

**Without Sibyl:**
- PM researches similar projects (1-2 hours)
- Breaks down into work streams (2 hours)
- Creates timeline and milestones (1 hour)
- Estimates effort and budget (2 hours)
- Writes proposal document (2 hours)
- Reviews and refines (1 hour)
- **Total: 8-10 hours**

**With Sibyl:**
- Run pipeline (5 minutes)
- Review and refine output (45 minutes)
- Customize for specific client (15 minutes)
- **Total: ~1 hour**

**Time saved: 7-9 hours per proposal**

## Key Techniques Showcased

### Sequential Thinking MCP (Critical!)
- **Initial scope expansion:** One-liner → comprehensive feature list
- **Architecture exploration:** Evaluate different technical approaches
- **Effort estimation:** Calculate person-weeks, timeline, budget
- **Branch thinking:** Explore alternative architectures

This demonstrates **true reasoning**, not just templating.

### category_naming
- **Organizes** features into parallelizable work streams
- **Enables** team structure planning
- **Creates** logical groupings for estimation

### checkpoint_naming
- **Breaks** project into phased delivery
- **Identifies** dependencies and sequencing
- **Creates** client-facing milestone plan

### quality_scoring
- **Validates** the breakdown meets standards
- **Flags** potential issues before client review
- **Ensures** professional output quality

## Variations to Try

### Different Project Types

```bash
# SaaS platform
--input '{"project_brief": "CRM for real estate agents with lead tracking"}'

# Content site
--input '{"project_brief": "News aggregation platform with personalized feeds"}'

# IoT product
--input '{"project_brief": "Smart home dashboard controlling multiple devices"}'

# Marketplace
--input '{"project_brief": "Freelancer marketplace connecting designers with clients"}'
```

### Different Constraints

```bash
# Budget-constrained
--input '{
  "project_brief": "Event planning platform",
  "timeline_weeks": 20,
  "budget_usd": 100000
}'

# Time-constrained
--input '{
  "project_brief": "Inventory management system",
  "timeline_weeks": 8,
  "must_have_features": ["barcode scanning", "real-time sync"]
}'

# Team-constrained
--input '{
  "project_brief": "Social fitness tracking app",
  "timeline_weeks": 16,
  "team_size": 3
}'
```

## Success Criteria

Pipeline succeeds if:
- ✓ Scope expanded from one-liner to comprehensive breakdown
- ✓ Work streams are logical and parallelizable
- ✓ Milestones have clear deliverables
- ✓ Estimates include effort, timeline, budget, team size
- ✓ Risks identified and mitigation suggested
- ✓ Quality score > 8.0/10
- ✓ Output is client-ready (professional formatting)

## Real-World Impact

### Sales Velocity
- Proposal turnaround: 1-2 days → Same day
- More proposals: 2-3/week → 10+/week
- Higher close rate: Better scoping = better fit

### Estimation Accuracy
- AI considers more factors than humans in less time
- Learns from similar projects
- Reduces "forgot to include X" errors

### Client Confidence
- Detailed breakdown shows expertise
- Demonstrates thoroughness
- Addresses risks proactively

## Troubleshooting

**Output is too generic:**
- Provide more context in project_brief
- Include industry-specific requirements
- Reference similar projects in prompts

**Estimates are unrealistic:**
- Adjust hourly rates in pipeline config
- Provide historical project data for calibration
- Override with manual adjustments

**Quality score is low:**
- Review validation step for specific issues
- Adjust quality criteria in config
- Run pipeline again with refined input

## Next Steps

After running this scenario:

1. **Customize for your domain:** Edit prompts, add industry patterns
2. **Integrate with CRM:** Auto-generate proposals from lead data
3. **Learn from actuals:** Compare estimates to actual project data
4. **Build proposal templates:** Use output to create reusable formats

## The Big Idea

This scenario demonstrates **creative AI augmentation**:
- Not just information retrieval (RAG)
- Not just templating (fill-in-the-blanks)
- **Actual reasoning** about project scope, architecture, effort

The Sequential Thinking MCP enables **multi-step problem-solving**:
1. Expand scope (thinking about features)
2. Explore architecture (considering trade-offs)
3. Estimate effort (reasoning about complexity)

Combined with Sibyl's AI generation techniques:
- Structure output (category_naming, checkpoint_naming)
- Validate quality (quality_scoring)
- Format for humans (templating)

**Result:** Professional project breakdowns in minutes, not hours.

This is **knowledge work automation** at its best.

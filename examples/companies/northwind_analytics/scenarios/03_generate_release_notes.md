# Scenario 3: Generate Release Notes from Docs

## Problem Statement

The Northwind Analytics product team is preparing to ship v2.1.0, which includes several new features:
- Alerts & Anomaly Detection
- Mobile app (iOS and Android)
- Advanced collaboration tools
- Performance improvements

The marketing team needs release notes that:
1. Highlight user benefits (not technical details)
2. Are exciting and easy to read
3. Follow the company's release note format
4. Are generated quickly (manual writing takes hours)

This scenario demonstrates combining structured data (feature list) with unstructured documentation to automatically generate polished release notes.

## Business Context

**Stakeholders**:
- **Product Team**: Provides feature list and wants consistent format
- **Marketing Team**: Needs user-friendly copy for announcements
- **Support Team**: Uses release notes for customer inquiries
- **Engineering**: Wants accurate technical details preserved

**Frequency**: Every 2-3 weeks (rapid release cycle)

**Challenge**: Manual release note writing is:
- Time-consuming (2-4 hours per release)
- Inconsistent (different writers, different styles)
- Often too technical (engineers write first drafts)
- Prone to missing features or details

**Goal**: Automate 80% of release note generation, leaving only final polish.

## Setup Required

### 1. Verify Feature Documentation

```bash
cd examples/companies/northwind_analytics

# Check that feature documentation exists
cat data/docs/feature_documentation.md | grep -A 10 "Alerts"
cat data/docs/feature_documentation.md | grep -A 10 "Collaboration"
```

### 2. Prepare Feature List

The pipeline accepts a list of feature keywords. These should match headings or topics in your documentation.

Example feature keywords:
- "alerts"
- "anomaly detection"
- "mobile app"
- "collaboration tools"
- "performance improvements"

### 3. No Database Required

Like Scenario 2, this is document-based (no SQL queries needed).

## Command to Run

### Basic Usage

```bash
cd examples/companies/northwind_analytics

sibyl pipeline run generate_release_notes \
  --workspace config/workspace.yaml \
  --input version="v2.1.0" \
  --input release_date="2024-11-15" \
  --input feature_keywords='["alerts", "anomaly detection", "mobile app", "collaboration"]' \
  --output-file results/release_notes_v2.1.0.md
```

### For a Major Release

```bash
sibyl pipeline run generate_release_notes \
  --workspace config/workspace.yaml \
  --input version="v3.0.0" \
  --input release_date="2024-12-01" \
  --input feature_keywords='["dashboard builder 2.0", "AI assistant", "custom integrations", "enterprise SSO", "API v2"]' \
  --output-file results/release_notes_v3.0.0.md
```

### For a Patch Release

```bash
sibyl pipeline run generate_release_notes \
  --workspace config/workspace.yaml \
  --input version="v2.0.3" \
  --input release_date="2024-10-22" \
  --input feature_keywords='["bug fixes", "performance"]' \
  --output-file results/release_notes_v2.0.3.md
```

## Expected Output

### Generated Release Notes for v2.1.0

````markdown
# Northwind Analytics v2.1.0
Released November 15, 2024

We're excited to announce v2.1.0 of Northwind Analytics! This release brings powerful new capabilities to help you stay on top of your data and collaborate more effectively with your team.

## 🎉 New Features

### Alerts & Anomaly Detection
Never miss an important metric change! Set up automated alerts that notify you when key metrics cross thresholds or show unusual patterns. Our ML-powered anomaly detection spots outliers before they become problems.

**What you can do:**
- Get notified via email, Slack, or SMS when MRR drops below targets
- Automatically detect unusual spikes or dips in daily metrics
- Set up smart alerts that learn your data patterns over time
- Configure alert schedules to avoid noise during off-hours

**Available on:** Professional and Enterprise plans

[Learn more: feature_documentation.md]

### 📱 Mobile Apps
Take Northwind Analytics on the go! Our brand-new iOS and Android apps let you check dashboards, run queries, and respond to alerts from anywhere.

**Features:**
- Full dashboard viewing optimized for phone and tablet
- Push notifications for critical alerts
- Offline mode for viewing cached data
- Touch-friendly filters and controls
- Quick actions from notification center

**Download now:**
- iOS: App Store
- Android: Google Play

[feature_documentation.md - Roadmap Q4 2024]

### 🤝 Enhanced Collaboration
Working with your team just got easier. Comment on dashboards, @mention teammates, and annotate charts to add business context.

**New capabilities:**
- Leave comments on specific charts or entire dashboards
- @mention colleagues to get their attention
- Annotate time-series charts to mark important events (e.g., "Q3 campaign launch")
- See who's viewed or edited shared dashboards
- Real-time collaboration (see teammate cursors)

**Perfect for:** Cross-functional teams, distributed workforces, and shared customer portals

[feature_documentation.md - Collaboration Tools]

## ✨ Improvements

### Faster Dashboard Loading
We've optimized our rendering engine for 40% faster dashboard load times. Complex dashboards with 10+ charts now load in under 2 seconds (P95).

### Smarter Auto-Complete
SQL query editor now suggests table joins and commonly used filters based on your query history.

### Better Error Messages
When something goes wrong, you'll see clear, actionable error messages instead of technical jargon.

## 🐛 Bug Fixes

- Fixed: Filters not persisting when sharing dashboard links
- Fixed: Date range picker showing incorrect timezone for APAC users
- Fixed: Export to PDF truncating long table columns
- Fixed: Race condition causing duplicate alert notifications
- Fixed: Memory leak in real-time dashboard updates

## 📚 Documentation

- **New:** Complete mobile app user guide
- **Updated:** Alerts setup tutorial with video walkthrough
- **Updated:** Collaboration features documentation

Visit help.northwindanalytics.com for full documentation.

## ⚡ Performance & Technical

- Backend API response times improved by 35% (P95: 120ms → 78ms)
- Reduced memory footprint by 25% for large datasets
- Upgraded to latest security patches (all dependencies current)
- Improved database connection pooling for better concurrency

## 🔄 Migration Notes

No action required! This update is backward-compatible and will be automatically rolled out to all customers over the next 48 hours.

**If you're on an Enterprise plan with on-premise deployment:**
- Review the upgrade guide at docs.northwindanalytics.com/upgrade/v2.1.0
- Estimated downtime: < 5 minutes
- Backup recommended before upgrading

## 🙏 Thank You

Thank you to the 47 customers who participated in our beta program and provided valuable feedback. Special shoutout to TechCorp, FinanceHub, and EuroTech Solutions for their detailed bug reports and feature suggestions.

## 💬 Questions or Feedback?

We'd love to hear what you think!
- **In-app:** Help > Submit Feedback
- **Email:** product@northwindanalytics.com
- **Community:** community.northwindanalytics.com

Happy analyzing! 📊

— The Northwind Analytics Team
````

### JSON Output

```json
{
  "release_notes": "[Markdown content as shown above]",
  "features_covered": [
    "alerts",
    "anomaly detection",
    "mobile app",
    "collaboration"
  ],
  "quality_score": 0.91,
  "metadata": {
    "version": "v2.1.0",
    "release_date": "2024-11-15",
    "word_count": 547,
    "sections": {
      "new_features": 4,
      "improvements": 3,
      "bug_fixes": 5,
      "documentation": 3
    },
    "sources_cited": [
      "feature_documentation.md",
      "dashboard_user_guide.md",
      "api_reference.md"
    ]
  }
}
```

### Console Output

```
[INFO] Loading workspace: config/workspace.yaml
[INFO] Initializing pipeline: generate_release_notes
[INFO] Step 1/4: retrieve_feature_docs
  → Query: "features alerts anomaly detection mobile app collaboration documentation"
  → Retrieved 10 documents (avg relevance: 0.85)
[INFO] Step 2/4: organize_features
  → Created 18 feature chunks (500 chars each)
  → Organized by feature keywords
[INFO] Step 3/4: create_release_notes
  → Generating release notes for v2.1.0
  → Date: 2024-11-15
  → Features: 4
  → Generated 1,124 tokens
[INFO] Step 4/4: validate_notes
  → Quality score: 0.91 ✓
  → Criteria:
    ✓ Proper formatting (Markdown headers, emojis)
    ✓ Includes all features (4/4 covered)
    ✓ User-focused language (not technical jargon)
    ✓ Actionable (includes links and next steps)
[SUCCESS] Pipeline completed in 16.8s

Release notes generated! See results/release_notes_v2.1.0.md
```

## What This Demonstrates

### 1. **Structured + Unstructured Data Fusion**
- **Structured**: Feature keywords, version, date (provided by user)
- **Unstructured**: Feature descriptions from docs (retrieved via RAG)
- **Output**: Polished release notes combining both

### 2. **Content Organization**
- Group features by type (New, Improvements, Fixes)
- Prioritize by importance (most impactful first)
- Add contextual information (pricing tier, availability)

### 3. **Tone and Style Control**
- Professional but friendly
- User-benefit focused (not technical)
- Emoji usage for visual appeal
- Consistent formatting

### 4. **Multi-Document Synthesis**
- Pull from multiple doc sources
- Combine overlapping information
- Remove redundancy
- Maintain coherence

### 5. **Quality Validation**
- Formatting checks (Markdown structure)
- Completeness checks (all features covered)
- Tone checks (user-friendly language)
- Length checks (not too long/short)

## Variations to Try

### 1. Generate Bug Fix Release

```bash
sibyl pipeline run generate_release_notes \
  --input version="v2.0.5" \
  --input release_date="2024-10-25" \
  --input feature_keywords='["bug fixes", "security patches"]'
```

### 2. Major Version Release

```bash
sibyl pipeline run generate_release_notes \
  --input version="v3.0.0" \
  --input release_date="2025-01-10" \
  --input feature_keywords='["redesigned UI", "API v2", "enterprise features", "pricing changes", "breaking changes"]'
```

### 3. Feature-Specific Release

```bash
sibyl pipeline run generate_release_notes \
  --input version="v2.2.0" \
  --input release_date="2024-11-30" \
  --input feature_keywords='["embedded analytics", "white labeling", "custom domains"]'
```

### 4. Weekly Sprint Release

```bash
sibyl pipeline run generate_release_notes \
  --input version="v2.1.1-sprint-45" \
  --input release_date="2024-11-08" \
  --input feature_keywords='["minor improvements", "performance"]'
```

## Troubleshooting

### Feature Not Found in Docs

```
Warning: Feature keyword "xyz" matched 0 documents
```

**Solution**:
- Check spelling: `feature_keywords='["alerts"]'` not `["allerts"]`
- Use broader terms: `["mobile"]` instead of `["iOS app version 1.0"]`
- Verify documentation covers the feature
- Add custom feature description if not in docs

### Release Notes Too Generic

```
Generated content lacks specifics
```

**Solution**:
- Provide more specific feature keywords
- Ensure documentation has detailed feature descriptions
- Increase `top_k` in retrieve step to get more context
- Lower temperature in generation config for more factual output

### Missing Sections

```
quality_score: 0.68 (missing improvements section)
```

**Solution**:
- Explicitly include `["improvements"]` in feature_keywords
- Adjust prompt to always include all sections
- Use a template-based generator for consistent structure

### Wrong Tone (Too Technical)

```
Generated notes use technical jargon
```

**Solution**:
- Adjust prompt: "Write for non-technical users"
- Set temperature higher (0.5-0.7) for more creative language
- Use examples in prompt showing desired tone
- Post-process with a "simplification" step

## Real-World Use Cases

### 1. **SaaS Product Teams**
- Weekly sprint releases
- Feature flag rollouts
- Bug fix patches
- Security updates

### 2. **Marketing Teams**
- Blog post content
- Email announcements
- Social media snippets
- Customer newsletters

### 3. **Support Teams**
- Customer-facing changelogs
- Onboarding documentation
- Knowledge base articles
- Training materials

### 4. **Sales Teams**
- Feature highlight sheets
- Competitive differentiation docs
- Customer upgrade justifications
- Demo preparation

## Integration Examples

### Automatic Release on Git Tag

```bash
#!/bin/bash
# .github/workflows/release.yml

VERSION=$(git describe --tags --abbrev=0)
DATE=$(date +%Y-%m-%d)

# Extract features from commit messages
FEATURES=$(git log --pretty=format:%s $PREV_TAG..$VERSION | grep -i "feat:" | sed 's/feat: //')

# Generate release notes
sibyl pipeline run generate_release_notes \
  --input version="$VERSION" \
  --input release_date="$DATE" \
  --input feature_keywords="$(echo $FEATURES | jq -R 'split(" ")')" \
  --output-file RELEASE_NOTES.md

# Create GitHub release
gh release create $VERSION --notes-file RELEASE_NOTES.md
```

### Slack Notification

```bash
# After generating release notes
NOTES=$(cat results/release_notes_v2.1.0.md)

curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🎉 New release ready!",
    "blocks": [
      {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "'"${NOTES:0:500}"'..."}
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Full Notes"},
            "url": "https://releases.northwindanalytics.com/v2.1.0"
          }
        ]
      }
    ]
  }'
```

## Comparison with Other Scenarios

| Aspect | Scenario 1 | Scenario 2 | Scenario 3 |
|--------|-----------|-----------|-----------|
| **Input** | Question | Dashboard name | Feature list |
| **Data** | SQL + Docs | Docs only | Docs only |
| **Output** | Analysis | Explanation | Release notes |
| **Style** | Analytical | Educational | Marketing |
| **Validation** | Numbers + citations | Readability | Format + completeness |

## Next Steps

After running this scenario:

1. **Edit the output**: Release notes are 80% done, polish the final 20%
2. **Try different versions**: Major, minor, patch releases
3. **Customize the format**: Edit the prompt in `pipelines.yaml`
4. **Automate it**: Integrate into your CI/CD pipeline
5. **Run Scenario 4**: Customer Health Summary (SQL-heavy)

## Learning Objectives

By completing this scenario, you will understand:

- ✅ Combining structured and unstructured data
- ✅ Content organization and prioritization
- ✅ Tone and style control in generation
- ✅ Multi-document synthesis
- ✅ Template-based generation
- ✅ Real-world automation workflows

## Related Scenarios

- **Scenario 1**: Revenue Analysis (SQL + RAG)
- **Scenario 2**: Explain Dashboard (pure RAG)
- **Scenario 4**: Customer Health Summary (SQL-heavy)

## Additional Resources

- **Template Customization**: `config/pipelines.yaml` (edit prompts)
- **Tone Control**: Sibyl generation techniques docs
- **CI/CD Integration**: Examples in `scripts/` directory

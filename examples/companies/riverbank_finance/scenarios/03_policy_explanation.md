# Scenario 3: Explain AML Policy for New Engineer

## Business Problem

RiverBank Finance onboards 5-10 new engineers per quarter. Each engineer needs to understand compliance requirements, but:
- Policy documents are 50+ pages of dense regulatory language
- Manual training takes 4-6 hours per engineer
- Engineers often have questions about specific policies
- Compliance team is overwhelmed with policy questions

We need a RAG-based system that can answer policy questions in beginner-friendly language.

## What This Scenario Demonstrates

### Techniques Used
- **Query Expansion**: Generate multiple query variations for better retrieval
- **RAG**: Semantic search over policy documents
- **Citation**: Include policy IDs and section references
- **AI Generation**: LLM-based explanation with examples

### Artifacts
- **Input**: Natural language question
- **Expanded Queries**: Multiple query variations
- **Policy Chunks**: Retrieved policy sections with relevance scores
- **Output**: Beginner-friendly explanation with citations

## Running the Scenario

### Command

```bash
sibyl pipeline run policy_explainer \
  --workspace examples/companies/riverbank_finance/config/workspace.yaml \
  --input question="What is structuring and how do we detect it?" \
  --input policy_area=AML
```

### Example Questions

```bash
# AML-related
--input question="What is the CTR filing threshold and when do I file?"
--input question="How do I identify a Politically Exposed Person (PEP)?"
--input question="What are the velocity monitoring requirements?"

# KYC-related
--input question="What documents do I need to verify customer identity?"
--input question="How often should we refresh KYC information?"

# Interest calculation
--input question="What formula should I use for compound interest?"
--input question="Why do we use a 360-day year for savings accounts?"

# Transaction limits
--input question="What are the daily transaction limits for standard accounts?"
```

## Expected Output

### Example 1: Structuring Question

**Input**: "What is structuring and how do we detect it?"

**Output**:
```markdown
# Policy Explanation: Structuring Detection

## Definition

**Structuring** (also called "smurfing") is a money laundering technique where someone breaks large transactions into smaller amounts to avoid regulatory reporting thresholds.

📚 **Policy Reference**: AML-001 (Anti-Money Laundering - Transaction Monitoring)

## Why It Matters

Under federal law (Bank Secrecy Act), financial institutions must file Currency Transaction Reports (CTRs) for cash transactions over $10,000. Criminals attempt to avoid CTRs by structuring transactions just below this threshold.

## How We Detect It

According to Policy AML-001, we monitor for these red flags:

### 1. **Multiple Transactions Below $10,000**
- **Indicator**: Customer makes 2+ transactions between $8,000-$10,000 within 30 days
- **Example**: Customer deposits $9,000 on Monday, $9,500 on Thursday, and $9,800 the following week
- **Why suspicious**: Pattern suggests deliberate avoidance of $10,000 threshold

### 2. **Round Dollar Amounts**
- **Indicator**: Large transactions in exact, round numbers (e.g., $9,000, $8,000)
- **Example**: Four deposits of exactly $9,000 each
- **Why suspicious**: Legitimate transactions rarely round to thousands

### 3. **Multiple Locations**
- **Indicator**: Customer uses different branches or ATMs for similar transactions
- **Example**: $9,000 withdrawal at Branch A, $9,000 at Branch B same day
- **Why suspicious**: Suggests intent to avoid detection by splitting across locations

## Our Detection Rules

**Automated Monitoring** (from Policy AML-001):
- ⚠️ **Alert if**: 3+ transactions between $8,000-$10,000 within 30 days
- 🚨 **Escalate if**: Pattern confirmed with round amounts or multiple locations
- 📊 **Risk Score**: Increases by 30-40 points for structuring indicators

## What To Do

If you detect potential structuring:

1. **Flag the transaction** in monitoring system
2. **Document the pattern**: Transaction IDs, amounts, dates, locations
3. **Notify Compliance Team** immediately
4. **Do NOT notify the customer** (per FinCEN confidentiality rules)
5. Compliance will investigate and potentially file SAR (Suspicious Activity Report)

## Example Scenario

**Customer Profile**: CUST-1004 (from our transaction data)
**Pattern Detected**:
- Oct 2: $9,000 cash withdrawal (ATM Branch 01)
- Oct 2: $9,500 cash withdrawal (ATM Branch 02)
- Oct 5: $9,800 cash withdrawal (ATM Branch 03)
- Oct 11: $9,200 cash withdrawal (ATM Branch 04)
- Oct 16: $9,100 cash withdrawal (ATM Branch 07)

**Total**: $46,600 over 2 weeks, all just below $10,000 threshold

**Action**: File SAR, enhanced due diligence required

## Related Policies

- **AML-001**: Transaction Monitoring and Suspicious Activity Detection
- **AML-003**: Currency Transaction Reporting (CTR)
- **AML-004**: Suspicious Activity Reporting (SAR)
- **TXN-002**: Regulatory Reporting Thresholds

## Key Regulations

- **Bank Secrecy Act (BSA)**: 31 USC 5311 et seq.
- **FinCEN Regulations**: 31 CFR 103
- **Penalties**: Up to $100,000 per violation + criminal penalties

## Learn More

- Read full policy: `data/docs/aml_policy.md` (Policy AML-001, page 3)
- Training module: "AML Red Flags and Detection" (required for all engineers)
- Questions? Contact Compliance Team: compliance@riverbankfinance.example

---

**Generated by RiverBank Finance Policy Explainer**
**Policies Cited**: AML-001, AML-003, AML-004, TXN-002
**Last Updated**: 2024-10-01
```

### Example 2: Compound Interest Formula

**Input**: "What formula should I use for compound interest?"

**Output**:
```markdown
# Policy Explanation: Compound Interest Calculation

## The Formula

For compound interest calculations, you **must** use this exact formula:

```
A = P(1 + r/n)^(nt)
```

Where:
- **A** = Final amount (principal + interest)
- **P** = Principal amount (initial investment/balance)
- **r** = Annual interest rate (as decimal, e.g., 0.05 for 5%)
- **n** = Number of times interest compounds per year
- **t** = Time in years

**Interest amount**: `I = A - P`

📚 **Policy Reference**: INT-002 (Compound Interest Requirements)

## Why This Formula?

Compound interest means "interest on interest" - each compounding period, interest is calculated on the accumulated amount, not just the original principal.

### ❌ Common Mistake (INCORRECT):
```python
# WRONG! This is simple interest per period, NOT compound
interest_per_period = principal * (rate / n)
total_interest = interest_per_period * (n * t)
```

### ✅ Correct Implementation:
```python
import math

final_amount = principal * math.pow(1 + (rate / n), n * t)
interest = final_amount - principal
```

## Example Calculation

**Scenario**: Customer has $10,000 savings account at 5% APR, compounded monthly, for 2 years

**Given**:
- P = $10,000
- r = 0.05
- n = 12 (monthly compounding)
- t = 2 years

**Calculation**:
```
A = 10,000 × (1 + 0.05/12)^(12×2)
A = 10,000 × (1.004167)^24
A = 10,000 × 1.104896
A = $11,048.96
```

**Interest earned**: $11,048.96 - $10,000 = **$1,048.96**

**Note**: Simple interest would only give $1,000 (10,000 × 0.05 × 2), so compound interest earns $48.96 more!

## Implementation Requirements

From Policy INT-002:

1. ✅ **Use `math.pow()` or `Math.pow()`** - proper exponentiation required
2. ✅ **Calculate each period's interest on accumulated amount** - not just principal
3. ✅ **Precision**: Use at least 6 decimal places in intermediate calculations
4. ✅ **Round final result** to 2 decimal places (cents)
5. ❌ **Never use simplified formulas** - policy violation

## Compounding Frequencies

Common values for `n`:

| Frequency | n value | Example |
|-----------|---------|---------|
| Daily | 365 | Savings accounts |
| Monthly | 12 | CDs, most accounts |
| Quarterly | 4 | Some business accounts |
| Annually | 1 | Bonds |

**Note**: For savings accounts, see special rule in Policy INT-003 about 360-day years!

## Testing Your Implementation

```python
def test_compound_interest():
    result = calculate_compound_interest(
        principal=10000,
        annual_rate=0.05,
        time_years=2,
        compound_frequency=12
    )

    expected = 11048.96
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"
```

## Related Policies

- **INT-001**: Simple Interest Calculation (for comparison)
- **INT-003**: Savings Account Interest (360-day year rule)
- **INT-004**: Loan Payment Calculation (uses compound interest)

## Regulations

- **Regulation DD (Truth in Savings)**: Requires accurate APY disclosure
- **TILA (Truth in Lending Act)**: Mandates correct interest calculations for loans

**Violations can result in**: Regulatory fines, customer remediation, audit findings

## Questions?

- See full policy: `data/docs/interest_rate_policy.md` (Policy INT-002)
- Code examples: `data/code/interest_calculator.py` (see `calculate_compound_interest()`)
- Contact: Treasury Department (treasury@riverbankfinance.example)

---

**Generated by RiverBank Finance Policy Explainer**
**Policies Cited**: INT-002, INT-001, INT-003
```

## Verification

### Query Expansion
```python
expanded_queries = [
    "What is structuring and how do we detect it?",
    "structuring detection methods money laundering",
    "identify structuring patterns transactions below reporting threshold",
    "currency transaction reporting CTR avoidance techniques"
]
```

### Retrieved Policy Chunks
```python
policy_chunks = [
    {
        "content": "Policy AML-001: Transaction Monitoring...\n\nStructuring (Smurfing)...",
        "source": "aml_policy.md",
        "relevance_score": 0.95,
        "policy_ids": ["AML-001"]
    },
    {
        "content": "Policy AML-003: Currency Transaction Reporting (CTR)...",
        "source": "aml_policy.md",
        "relevance_score": 0.87,
        "policy_ids": ["AML-003"]
    },
    # ...
]
```

## What's Demonstrated

### 1. Query Expansion
Shows techniques for improving RAG retrieval:
- Original question + variations
- Terminology expansion
- Contextual enrichment

### 2. Semantic Search
Demonstrates:
- Embedding-based search over policy documents
- Relevance scoring
- Top-K retrieval

### 3. Citation Generation
Shows how to:
- Track source documents
- Extract policy IDs
- Include references in output

### 4. Beginner-Friendly Explanation
Demonstrates LLM capabilities:
- Simplify complex regulatory language
- Provide practical examples
- Explain "why" behind policies
- Include code samples when relevant

## Next Steps

- Try questions about different policy areas
- Adjust retrieval parameters (top_k, chunk_size)
- Add conversational follow-up questions
- Build Slack/Teams bot integration

---

**Related Scenarios**:
- Scenario 1: Code Compliance Check
- Scenario 2: Risk Graph Analysis

# Scenario 1: Find Incorrect Interest Calculations in Code

## Business Problem

RiverBank Finance's internal audit discovered potential compliance issues in the interest calculation module. The code review team found that:

1. **`calculate_compound_interest()`** appears to use an incorrect formula
2. **`calculate_savings_account_interest()`** may be using wrong day-count convention
3. Several functions lack clear policy references

Manual code review is time-consuming and error-prone. We need an automated system to:
- Parse Python banking code and build AST
- Search for interest calculation patterns
- Cross-reference with policy documents (INT-001, INT-002, INT-003)
- Generate compliance reports flagging violations

## What This Scenario Demonstrates

### Techniques Used
- **Code Analysis → AST**: Parse Python code using AST Server MCP → ASTArtifact
- **Pattern Matching**: Search AST for calculation functions
- **RAG**: Retrieve relevant policy sections from markdown documents
- **AI Generation**: Generate structured compliance report

### Artifacts
- **Input**: Python source code file
- **ASTArtifact**: Typed AST representation with nodes and location info
- **Policy Context**: Retrieved policy sections via RAG
- **Output**: Compliance report with violations and severity

### MCPs Involved
1. **AST Server** (or Serena): Parse Python code to AST
2. **Vector Store**: RAG for policy document retrieval
3. **LLM**: Generate compliance analysis

## Setup

### Prerequisites
- AST Server MCP installed and configured
- Policy documents in `data/docs/` (already included)
- OpenAI API key for LLM and embeddings

### Data Required
- `data/code/interest_calculator.py` - Banking code with intentional bugs
- `data/docs/interest_rate_policy.md` - Interest calculation policies

## Running the Scenario

### Command

```bash
sibyl pipeline run code_compliance_check \
  --workspace examples/companies/riverbank_finance/config/workspace.yaml \
  --input file_path=examples/companies/riverbank_finance/data/code/interest_calculator.py \
  --input policy_reference=INT-002 \
  --verbose
```

### Alternative: Via MCP Tool

If using Sibyl as MCP server with AI assistant:

```
check_code_compliance(
  file_path="examples/companies/riverbank_finance/data/code/interest_calculator.py",
  policy_reference="INT-002"
)
```

## Expected Output

### Pipeline Flow

```
Step 1: load_code
  ↓ Reads interest_calculator.py
  ✓ Output: code_content (Python source)

Step 2: build_ast
  ↓ AST Server MCP parses code
  ✓ Output: ASTArtifact with parsed syntax tree

Step 3: find_calculations
  ↓ Pattern matching on AST
  ✓ Output: List of calculation patterns found
    - calculate_simple_interest (line 15)
    - calculate_compound_interest (line 35) ⚠️
    - calculate_savings_account_interest (line 65) ⚠️
    - calculate_loan_payment (line 95)
    - apply_promotional_rate (line 130)

Step 4: retrieve_policies
  ↓ RAG query: "interest calculation formula compound INT-002"
  ✓ Output: Policy sections from interest_rate_policy.md
    - Policy INT-001: Simple Interest Formula
    - Policy INT-002: Compound Interest Requirements ← KEY
    - Policy INT-003: Savings Account Interest (360-day year) ← KEY

Step 5: generate_report
  ↓ LLM analyzes code vs. policies
  ✓ Output: Compliance Report (see below)
```

### Compliance Report Structure

```yaml
compliance_report:
  file: "interest_calculator.py"
  policies_checked:
    - "INT-001"
    - "INT-002"
    - "INT-003"

  violations:
    - violation_id: "CALC-001"
      function: "calculate_compound_interest"
      location: "Line 35-60"
      severity: "CRITICAL"
      policy: "INT-002"
      issue: "Incorrect compound interest formula"
      details: |
        The implementation uses: interest_per_period * total_periods
        Policy INT-002 requires: P(1 + r/n)^(nt) - P

        Current code (lines 51-54):
          interest_per_period = principal * period_rate
          total_interest = interest_per_period * total_periods

        This is simple interest per period, NOT compound interest!
      impact: "Customers are being charged incorrect interest (likely undercharged)"
      remediation: |
        Replace with correct formula:
          final_amount = principal * math.pow(1 + period_rate, total_periods)
          total_interest = final_amount - principal

      customer_impact: "Estimated 5-10% calculation error"

    - violation_id: "CALC-002"
      function: "calculate_savings_account_interest"
      location: "Line 65-90"
      severity: "HIGH"
      policy: "INT-003"
      issue: "Incorrect day-count convention"
      details: |
        The implementation uses 365-day year (line 80):
          daily_rate = annual_rate / 365

        Policy INT-003 requires 360-day year (30/360 convention):
          daily_rate = annual_rate / 360

      impact: "Customers are being underpaid interest on savings accounts"
      remediation: |
        Change line 80 from:
          daily_rate = annual_rate / 365
        To:
          daily_rate = annual_rate / 360

      customer_impact: "~1.4% underpayment to customers"

    - violation_id: "POLICY-001"
      function: "apply_promotional_rate"
      location: "Line 130-145"
      severity: "MEDIUM"
      policy: "N/A"
      issue: "Missing policy reference"
      details: |
        Function lacks reference to policy governing promotional rates.
        Tier bonuses and loyalty bonuses appear to be hard-coded without
        policy documentation.

      impact: "Risk of inconsistent application, audit findings"
      remediation: |
        1. Document promotional rate policy (create INT-005 if needed)
        2. Add policy reference in docstring
        3. Validate thresholds against policy

  compliant_functions:
    - function: "calculate_simple_interest"
      policy: "INT-001"
      status: "COMPLIANT"
      notes: "Correctly implements I = P * R * T formula"

    - function: "calculate_loan_payment"
      policy: "INT-004"
      status: "COMPLIANT"
      notes: "Correctly implements amortization formula"

  summary:
    total_functions: 5
    violations: 3
    critical: 1
    high: 1
    medium: 1
    low: 0

  recommended_actions:
    - priority: 1
      action: "CRITICAL: Fix compound interest formula in calculate_compound_interest()"
      owner: "Engineering"
      deadline: "Immediate (within 24 hours)"

    - priority: 2
      action: "HIGH: Fix day-count convention in calculate_savings_account_interest()"
      owner: "Engineering"
      deadline: "Within 48 hours"

    - priority: 3
      action: "MEDIUM: Add policy reference to apply_promotional_rate()"
      owner: "Product/Compliance"
      deadline: "Within 1 week"

    - priority: 4
      action: "Review all customer accounts affected by incorrect calculations"
      owner: "Operations"
      deadline: "Within 1 week"

    - priority: 5
      action: "Prepare customer remediation plan if needed"
      owner: "Compliance/Legal"
      deadline: "Within 2 weeks"

  regulatory_impact:
    - regulation: "Regulation DD (Truth in Savings)"
      risk: "HIGH"
      notes: "Incorrect APY calculations may violate disclosure requirements"

    - regulation: "TILA (Truth in Lending)"
      risk: "HIGH"
      notes: "Incorrect loan calculations may violate TILA"
```

## Verification

### ASTArtifact Structure

The pipeline should produce an ASTArtifact with this structure:

```python
ast_artifact = ASTArtifact(
    root=ASTNode(
        type="Module",
        properties={},
        children=[
            ASTNode(
                type="FunctionDef",
                properties={"name": "calculate_simple_interest"},
                location=Location(file="interest_calculator.py", start_line=15, ...)
            ),
            ASTNode(
                type="FunctionDef",
                properties={"name": "calculate_compound_interest"},
                location=Location(file="interest_calculator.py", start_line=35, ...)
            ),
            # ... more functions
        ]
    ),
    language="python",
    source_file="interest_calculator.py"
)

# Query for calculation functions
calc_functions = ast_artifact.query("FunctionDef")
assert len(calc_functions) >= 5

# Verify compound interest function found
compound_func = [f for f in calc_functions if "compound" in f.properties.get("name", "")]
assert len(compound_func) == 1
```

### Policy Retrieval

RAG should retrieve relevant policy sections:

```python
policy_chunks = [
    {
        "content": "Policy INT-002: Compound Interest Requirements\n\nFormula: A = P(1 + r/n)^(nt)...",
        "source": "interest_rate_policy.md",
        "relevance_score": 0.92
    },
    {
        "content": "Policy INT-003: Savings Account Interest\n\nDay Count Convention: 360-day year...",
        "source": "interest_rate_policy.md",
        "relevance_score": 0.85
    },
    # ...
]

assert any("INT-002" in chunk["content"] for chunk in policy_chunks)
assert any("360" in chunk["content"] for chunk in policy_chunks)
```

## What's Demonstrated

### 1. Code → AST → Typed Artifact

This scenario shows the complete flow from source code to typed AST:
- File reading
- MCP call to AST Server
- Construction of ASTArtifact with proper structure
- Querying and traversal of AST

### 2. Pattern Detection in AST

Demonstrates searching for:
- Function names matching patterns (e.g., contains "calculate")
- Specific syntax elements (e.g., `math.pow()`)
- Comments with policy references

### 3. Cross-MCP Integration

Shows how AST analysis (AST Server) integrates with RAG (embeddings + vector store):
- AST patterns inform what policies to look up
- Policy content provides context for LLM analysis
- LLM combines both to generate report

### 4. Policy-Driven Code Review

This is a real-world compliance use case:
- Policies define requirements
- Code must implement policies correctly
- Automated review catches violations
- Clear remediation guidance

## Next Steps

### For Users
1. Run the scenario and examine the full report
2. Look at the buggy code in `interest_calculator.py` lines 35-60 and 65-90
3. Read the policies in `interest_rate_policy.md` to understand requirements
4. Try analyzing other code files (e.g., `transaction_processor.js`)

### For Developers
1. Add more pattern detection rules (e.g., find all policy references)
2. Extend to JavaScript/TypeScript using Serena MCP
3. Build CI/CD integration for automated compliance checks
4. Add fix suggestions (code transformations)

### For Compliance Teams
1. Customize policy documents with your organization's requirements
2. Define severity thresholds for different violation types
3. Build reporting dashboards for compliance status
4. Integrate with case management systems

## Troubleshooting

### No violations detected
- Check that AST parsing is working: `sibyl debug ast --file data/code/interest_calculator.py`
- Verify policy retrieval: `sibyl debug rag --query "compound interest" --source data/docs/`
- Review LLM prompt to ensure it includes specific formula checks

### AST parsing fails
- Ensure code file is valid Python (no syntax errors)
- Check AST Server MCP is running: `sibyl mcp list`
- Try alternative: Serena MCP for JavaScript files

### Policy retrieval returns empty
- Ensure vector store is initialized: Check for `.riverbank_vector_store.duckdb`
- Re-embed documents: `sibyl embed --source data/docs/ --store vector_store.default`
- Check embedding API key is set: `echo $OPENAI_API_KEY`

---

**Related Scenarios**:
- Scenario 2: Risk Graph Analysis (transaction patterns)
- Scenario 3: Policy Explainer (RAG Q&A)

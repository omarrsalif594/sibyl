# Scenario 2: Diagnose Failing Training Job with SessionHandle

## Overview
This scenario demonstrates using SessionHandle for multi-turn code analysis to diagnose why a training job failed. The pipeline maintains conversation context across multiple analysis steps to identify root causes and generate recommendations.

## ML Platform Problem
One of your team's training jobs crashed at step 1523 with a NaN loss error. As the platform engineer, you need to:
1. Analyze the error logs to understand what happened
2. Examine the training code for bugs or misconfigurations
3. Correlate the error with specific code issues
4. Use multi-turn reasoning to identify the root cause
5. Generate actionable recommendations for fixing the issue

## Features Demonstrated
- **SessionHandle**: Persistent conversation context across multiple MCP calls
- **Multi-turn Reasoning**: Chain of analysis steps building on previous context
- **Context Retention**: Session maintains understanding of code, errors, and hypotheses
- **ExternalHandle**: Deep Code Reasoning MCP integration
- **Control Flow**: Conditional code analysis based on configuration

## Prerequisites
1. Deep Code Reasoning MCP server running (code analysis)
2. Vertex Foundry workspace configured
3. Failed run data available (run_20250116_091523)
4. Training code available for analysis

## Setup

### 1. Verify Deep Code Reasoning MCP is running
```bash
curl http://localhost:8082/health
```

### 2. Check that failed run data exists
```bash
ls examples/companies/vertex_foundry/data/runs/run_20250116_091523.json
ls examples/companies/vertex_foundry/data/experiments/logs/run_20250116_091523_error.log
```

### 3. Verify training code
```bash
ls examples/companies/vertex_foundry/data/code/train_model.py
```

## Execution

### Command
```bash
sibyl pipeline run diagnose_failure \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input run_id="run_20250116_091523" \
  --input include_code_analysis=true \
  --verbose
```

### Quick diagnosis (skip code analysis)
```bash
sibyl pipeline run diagnose_failure \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input run_id="run_20250116_091523" \
  --input include_code_analysis=false
```

## Expected Behavior

### Phase 1: Load Run Data & Logs
```
[2025-01-22 11:00:00] INFO: Starting pipeline: diagnose_failure
[2025-01-22 11:00:00] INFO: Step 1/9: load_run_data
[2025-01-22 11:00:00] INFO: Loading run metadata: run_20250116_091523
[2025-01-22 11:00:01] INFO: Run metadata loaded:
  - Status: failed
  - Failure step: 1523
  - Error: RuntimeError: Loss became NaN at step 1523
  - Hyperparameters: lr=0.01, batch_size=32, dropout=0.5
  - Duration: 1612 seconds
  - Cost: $0.89

[2025-01-22 11:00:01] INFO: Loading error log...
[2025-01-22 11:00:01] INFO: Error log loaded: 156 lines
```

### Phase 2: Extract Error Patterns
```
[2025-01-22 11:00:01] INFO: Step 2/9: extract_error_patterns
[2025-01-22 11:00:02] INFO: Analyzing error log for patterns...
[2025-01-22 11:00:03] INFO: Error patterns identified:
  1. Loss gradient explosion detected (grad_norm=1247.34)
  2. NaN first appeared at step 1521
  3. Loss spike: 0.189 → 234.56 → 3456.789 → NaN
  4. Gradient explosion in fully connected layers
  5. Warning: Loss function config: CrossEntropyLoss(reduction='sum')

[2025-01-22 11:00:03] INFO: Error context extracted:
  - Last valid loss values: [0.145, 0.156, 0.167, 0.178, 0.189]
  - Gradient norms at failure:
    - fc1.weight: 1247.34
    - fc2.weight: 892.45
    - conv layers: normal range
  - Possible causes listed in log:
    1. Learning rate too high (current: 0.01)
    2. Loss function misconfiguration
    3. Batch normalization issues
    4. Data preprocessing errors
```

### Phase 3: Create SessionHandle for Code Analysis
```
[2025-01-22 11:00:03] INFO: Step 3/9: initialize_analysis_session
[2025-01-22 11:00:03] INFO: Connecting to Deep Code Reasoning MCP...
[2025-01-22 11:00:04] INFO: Creating persistent analysis session...
[2025-01-22 11:00:05] INFO: SessionHandle created: session_xyz789abc123
[2025-01-22 11:00:05] INFO: Session configuration:
  - Type: persistent
  - Context retention: enabled
  - Max turns: 10
  - Model: claude-sonnet-4-5
```

### Phase 4: Analyze Training Code (Turn 1)
```
[2025-01-22 11:00:05] INFO: Step 4/9: analyze_training_code
[2025-01-22 11:00:05] INFO: Using SessionHandle: session_xyz789abc123
[2025-01-22 11:00:05] INFO: Analyzing training code for bugs...
[2025-01-22 11:00:05] INFO: Focus areas:
  - Loss function configuration
  - Optimizer setup
  - Gradient handling

[2025-01-22 11:00:08] INFO: Deep Code Reasoning MCP - Turn 1
[2025-01-22 11:00:10] INFO: Code issues identified:
  1. BUG: train_model.py:85 - CrossEntropyLoss(reduction='sum')
     - Expected: reduction='mean'
     - Impact: Loss scaled by batch_size, gradients ~32x larger
     - Severity: HIGH
     - Line: criterion = nn.CrossEntropyLoss(reduction='sum')

  2. WARNING: train_model.py:78 - High learning rate (0.01) with Adam
     - Recommended range: 0.0001 - 0.001 for Adam
     - Current: 0.01 (10-100x too high)
     - Severity: MEDIUM

  3. INFO: No gradient clipping implemented
     - Recommended: Add gradient clipping for stability
     - Severity: LOW

[2025-01-22 11:00:10] INFO: Suspicious patterns detected:
  - Loss function bug compounds with high learning rate
  - No safeguards against gradient explosion
  - Comment on line 82: "# BUG: Using wrong reduction..."
```

### Phase 5: Correlate Errors with Code (Turn 2 - Same Session)
```
[2025-01-22 11:00:10] INFO: Step 5/9: correlate_errors_with_code
[2025-01-22 11:00:10] INFO: Using same SessionHandle: session_xyz789abc123
[2025-01-22 11:00:10] INFO: Cross-referencing error patterns with code issues...

[2025-01-22 11:00:13] INFO: Deep Code Reasoning MCP - Turn 2 (context preserved)
[2025-01-22 11:00:16] INFO: Correlations found:
  1. STRONG CORRELATION (confidence: 95%)
     - Error: "Loss gradient explosion detected (grad_norm=1247.34)"
     - Code: CrossEntropyLoss(reduction='sum') at line 85
     - Explanation:
       - reduction='sum' causes loss to be sum(batch_losses)
       - With batch_size=32, loss is 32x larger
       - Gradients are 32x larger
       - Combined with lr=0.01 (already 10x too high), effective learning rate is 320x too high
       - This explains rapid training (initially) followed by explosion

  2. STRONG CORRELATION (confidence: 90%)
     - Error: "Loss spike: 0.189 → 234.56 → 3456.789 → NaN"
     - Code: High learning rate (0.01) + wrong loss reduction
     - Explanation:
       - At step 1520, weight updates became too large
       - Exponential divergence pattern typical of excessive learning rate
       - 3 steps from stable to NaN indicates critical instability

  3. MEDIUM CORRELATION (confidence: 70%)
     - Error: "Gradient explosion in fully connected layers"
     - Code: No gradient clipping
     - Explanation:
       - FC layers have large weight matrices
       - More susceptible to gradient explosion
       - Gradient clipping would have prevented this
```

### Phase 6: Multi-turn Root Cause Reasoning (Turn 3 - Same Session)
```
[2025-01-22 11:00:16] INFO: Step 6/9: identify_root_cause
[2025-01-22 11:00:16] INFO: Using same SessionHandle: session_xyz789abc123
[2025-01-22 11:00:16] INFO: Performing deep iterative reasoning...
[2025-01-22 11:00:16] INFO: Chain-of-thought analysis enabled

[2025-01-22 11:00:20] INFO: Deep Code Reasoning MCP - Turn 3 (context preserved)
[2025-01-22 11:00:25] INFO: Root cause analysis:

Reasoning Chain:
1. Initial hypothesis: High learning rate caused explosion
   - Evidence: lr=0.01 is 10-100x recommended for Adam
   - Counter-evidence: Training was stable for 12 epochs (1520 steps)
   - Conclusion: Partially true, but not sufficient explanation

2. Secondary hypothesis: Loss function bug is primary cause
   - Evidence: reduction='sum' scales loss by batch_size=32
   - Evidence: Effective learning rate is 0.01 * 32 = 0.32 (extremely high)
   - Evidence: Similar experiments with lr=0.01 but reduction='mean' succeeded
   - Conclusion: This is the primary issue

3. Temporal analysis: Why did it fail at step 1523, not earlier?
   - Evidence: Training loss decreased normally initially
   - Insight: Model converged to sharp local minimum
   - Insight: At convergence, gradients become more sensitive
   - Insight: Large weight update at step 1520 pushed model off manifold
   - Conclusion: Bug was present from start, manifested after convergence

ROOT CAUSE IDENTIFIED (confidence: 98%):
  Primary: CrossEntropyLoss(reduction='sum') instead of reduction='mean'
  Secondary: Learning rate 0.01 too high for Adam optimizer
  Interaction: Combined effect created effective learning rate of 0.32
  Trigger: Model reached convergence at step ~1500, became sensitive to large updates

This is a CODING BUG, not a hyperparameter issue.
```

### Phase 7: Generate Recommendations (Turn 4 - Same Session)
```
[2025-01-22 11:00:25] INFO: Step 7/9: generate_recommendations
[2025-01-22 11:00:25] INFO: Using same SessionHandle: session_xyz789abc123
[2025-01-22 11:00:25] INFO: Generating fix recommendations...

[2025-01-22 11:00:28] INFO: Deep Code Reasoning MCP - Turn 4 (context preserved)
[2025-01-22 11:00:30] INFO: Recommendations generated:

IMMEDIATE FIXES (Required):
1. Fix loss function reduction
   - File: data/code/train_model.py
   - Line: 85
   - Change: criterion = nn.CrossEntropyLoss(reduction='sum')
   - To: criterion = nn.CrossEntropyLoss(reduction='mean')
   - Impact: Resolves gradient explosion
   - Priority: CRITICAL

2. Reduce learning rate
   - File: data/code/train_model.py
   - Line: 78
   - Change: lr=0.01
   - To: lr=0.001 (recommended) or lr=0.0001 (conservative)
   - Impact: Stabilizes training
   - Priority: HIGH

RECOMMENDED IMPROVEMENTS:
3. Add gradient clipping
   - File: data/code/train_model.py
   - Location: After loss.backward(), before optimizer.step()
   - Code: torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
   - Impact: Prevents gradient explosion
   - Priority: MEDIUM

4. Add loss validation
   - File: data/code/train_model.py
   - Location: After loss calculation
   - Code: assert not torch.isnan(loss), f"NaN loss at step {step}"
   - Impact: Fail fast on training issues
   - Priority: LOW

CODE FIXES:
```python
# FIX 1: train_model.py, line 85
# WRONG:
criterion = nn.CrossEntropyLoss(reduction='sum')

# CORRECT:
criterion = nn.CrossEntropyLoss(reduction='mean')

# FIX 2: train_model.py, line 78
# WRONG:
parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')

# CORRECT:
parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
# Note: Default is already correct, but user override to 0.01 caused issue

# FIX 3: train_model.py, after line 63 (in train_epoch function)
loss.backward()
# ADD:
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
# THEN:
optimizer.step()
```
```

### Phase 8: Create Diagnostic Report
```
[2025-01-22 11:00:30] INFO: Step 8/9: create_report
[2025-01-22 11:00:31] INFO: Generating comprehensive diagnostic report...

[2025-01-22 11:00:32] INFO: Diagnostic report created:

================================================================================
TRAINING FAILURE DIAGNOSTIC REPORT
================================================================================
Run ID: run_20250116_091523
Analysis Date: 2025-01-22 11:00:32
Analysis Method: Deep code reasoning with multi-turn session
Confidence: 98%

FAILURE SUMMARY
---------------
Status: Failed at step 1523
Error: RuntimeError: Loss became NaN
Duration: 1612 seconds (26.9 minutes)
Cost: $0.89
Epoch: 12 of 50

HYPERPARAMETERS
---------------
Learning Rate: 0.01
Batch Size: 32
Dropout: 0.5
Weight Decay: 0.0001
Optimizer: Adam

ROOT CAUSE
----------
PRIMARY ISSUE: Loss function misconfiguration
  - CrossEntropyLoss configured with reduction='sum' instead of 'mean'
  - Causes loss and gradients to be scaled by batch_size (32x too large)
  - Combined with high learning rate (0.01), effective LR becomes 0.32
  - This is 320x higher than recommended for Adam optimizer

SECONDARY ISSUE: Learning rate too high
  - User specified lr=0.01, recommended range is 0.0001-0.001
  - Alone might be manageable, but combines with loss bug

TRIGGER: Model convergence
  - Bug was present from start but didn't immediately cause failure
  - At step ~1500, model reached local minimum
  - Became sensitive to large weight updates
  - Large update at step 1520 caused divergence

ERROR PROGRESSION
-----------------
Step 1520: Loss gradient explosion detected (grad_norm=1247.34)
Step 1521: NaN detected in model outputs
Step 1522: NaN detected in loss
Step 1523: Training terminated

Loss values: 0.189 → 234.56 → 3456.789 → NaN (3-step explosion)

RECOMMENDATIONS
---------------
1. [CRITICAL] Fix loss function reduction in train_model.py line 85
2. [HIGH] Reduce learning rate to 0.001 or lower
3. [MEDIUM] Add gradient clipping (max_norm=1.0)
4. [LOW] Add NaN detection for early failure

ESTIMATED FIX TIME: 5 minutes
ESTIMATED RERUN COST: $4.50 (full training)

NEXT STEPS
----------
1. Apply code fixes to train_model.py
2. Rerun experiment with corrected code
3. Monitor for gradient norms in first 100 steps
4. Expected outcome: Stable training, val_acc ~82-84%

================================================================================
```

### Phase 9: Cleanup Session
```
[2025-01-22 11:00:32] INFO: Step 9/9: cleanup_session
[2025-01-22 11:00:32] INFO: Closing SessionHandle: session_xyz789abc123
[2025-01-22 11:00:32] INFO: Session statistics:
  - Total turns: 4
  - Context maintained: yes
  - Analysis depth: deep
  - Total tokens: ~8,500

[2025-01-22 11:00:32] SUCCESS: Pipeline completed successfully
```

## Pipeline Outputs

```json
{
  "diagnosis": {
    "root_cause": "Loss function misconfiguration: CrossEntropyLoss(reduction='sum') should be reduction='mean'",
    "confidence": 0.98,
    "primary_issue": "loss_function_bug",
    "secondary_issues": ["learning_rate_too_high"],
    "trigger": "model_convergence_sensitivity",
    "failure_step": 1523,
    "failure_type": "gradient_explosion",
    "estimated_fix_time_minutes": 5
  },
  "recommendations": [
    {
      "priority": "CRITICAL",
      "type": "code_fix",
      "file": "data/code/train_model.py",
      "line": 85,
      "description": "Change CrossEntropyLoss(reduction='sum') to reduction='mean'",
      "code_fix": "criterion = nn.CrossEntropyLoss(reduction='mean')"
    },
    {
      "priority": "HIGH",
      "type": "hyperparameter_adjustment",
      "parameter": "learning_rate",
      "current_value": 0.01,
      "recommended_value": 0.001,
      "description": "Reduce learning rate to recommended range for Adam"
    },
    {
      "priority": "MEDIUM",
      "type": "code_improvement",
      "file": "data/code/train_model.py",
      "description": "Add gradient clipping",
      "code_fix": "torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)"
    }
  ],
  "root_cause": "Loss function misconfiguration combined with high learning rate"
}
```

## Key Technical Details

### SessionHandle Implementation
```python
# Internal representation (conceptual)
class SessionHandle:
    session_id: str = "session_xyz789abc123"
    mcp_server: str = "deep_code_reasoning"
    context: ConversationContext  # Retained across turns
    turn_count: int = 0
    max_turns: int = 10

    async def send_message(self, message: str) -> Response:
        # Sends message with full conversation context
        # Context includes:
        # - Previous questions and answers
        # - Code files analyzed
        # - Hypotheses explored
        # - Evidence gathered
        self.turn_count += 1
        return await self.mcp_server.chat(self.session_id, message, self.context)
```

### Multi-turn Reasoning Benefits
1. **Context Preservation**: Each turn builds on previous understanding
2. **Hypothesis Refinement**: Can test and refine theories
3. **Evidence Accumulation**: Gathers supporting/contradicting evidence
4. **Chain of Thought**: Explicit reasoning chain visible
5. **Efficiency**: No need to re-explain code/errors each turn

## Verification

### Check diagnostic report was generated
```bash
ls -lh diagnosis_output.json
jq '.diagnosis.root_cause' diagnosis_output.json
```

### Verify session was used correctly
```bash
# Check logs for session creation and reuse
grep "SessionHandle" vertex_foundry.log

# Should show:
# - Created: session_xyz789abc123
# - Turn 1: analyze_training_code
# - Turn 2: correlate_errors_with_code
# - Turn 3: identify_root_cause
# - Turn 4: generate_recommendations
# - Closed: session_xyz789abc123
```

### Apply recommended fix
```bash
# Review the fix
jq '.recommendations[0]' diagnosis_output.json

# Apply the fix manually
vim examples/companies/vertex_foundry/data/code/train_model.py
# Change line 85: reduction='sum' → reduction='mean'
```

## Troubleshooting

### Session not created
- Verify Deep Code Reasoning MCP is running
- Check workspace.yaml connection config
- Ensure session_type: "persistent" in config

### Context not preserved between turns
- Verify SessionHandle is passed to each step
- Check session hasn't expired (timeout)
- Ensure same session ID used across steps

### Code analysis incomplete
- Check that code files exist
- Verify MCP has access to filesystem
- Increase analysis_depth in config

## What This Demonstrates

1. **SessionHandle**: Persistent conversation context across multiple MCP calls
2. **Multi-turn Reasoning**: Building understanding progressively through conversation
3. **Context Retention**: Each analysis step builds on previous insights
4. **Chain of Thought**: Explicit reasoning process visible and debuggable
5. **MCP Integration**: Deep Code Reasoning MCP for sophisticated code analysis
6. **Control Flow**: Conditional code analysis based on input flags
7. **Practical Value**: Real bug diagnosis with actionable recommendations

This scenario showcases how SessionHandle enables sophisticated multi-step analysis workflows that would be impossible with stateless API calls.

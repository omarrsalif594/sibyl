# Scenario 2: Build Risk Graph and List Top-Risk Customers

## Business Problem

RiverBank Finance's compliance team needs to identify high-risk customers based on transaction patterns. They're looking for:
- **Structuring**: Multiple transactions just below $10,000 CTR threshold
- **Circular transactions**: Money moving in circles between accounts
- **Velocity abuse**: Too many transactions in short time windows
- **Amount escalation**: Transaction sizes growing suspiciously

Manual review of 10,000+ customers is impractical. They need automated graph-based risk detection.

## What This Scenario Demonstrates

### Techniques Used
- **Data Loading**: JSON transaction data ingestion
- **Graph Construction**: Build graph using Graphiti MCP → GraphArtifact
- **Graph Metrics**: Calculate centrality using NetworkX → GraphMetricsArtifact
- **Risk Ranking**: Identify high-risk nodes by centrality scores
- **AI Analysis**: LLM-based risk report generation

### Artifacts
- **Input**: Transaction JSON (customers, transactions, suspicious patterns)
- **GraphArtifact**: Typed graph with nodes (customers) and edges (transactions)
- **GraphMetricsArtifact**: Centrality scores, rankings, and metrics
- **Output**: Risk report with top-N high-risk customers

### MCPs Involved
1. **Graphiti**: Graph database for transaction relationships
2. **NetworkX** (via Sibyl): Centrality calculation algorithms
3. **LLM**: Risk analysis and report generation

## Setup

### Prerequisites
- Graphiti MCP installed and running
- Neo4j or compatible graph database (if required by Graphiti)
- Transaction data in `data/transactions/transactions.json`

### Data Structure

```json
{
  "customers": [
    {"customer_id": "CUST-1001", "risk_level": "low", ...},
    {"customer_id": "CUST-1004", "risk_level": "high", "notes": "Structuring pattern"}
  ],
  "transactions": [
    {"id": "TXN-001", "customer_id": "CUST-1001", "amount": 500, "counterparty": "MERCHANT", ...},
    {"id": "TXN-004", "customer_id": "CUST-1004", "amount": 9000, "counterparty": "ATM", "flags": ["structuring_indicator"]}
  ],
  "suspicious_patterns": {
    "structuring": {"customers": ["CUST-1004", "CUST-1010"], ...},
    "circular_transactions": {"customers": ["CUST-1006", "CUST-1007"], ...}
  }
}
```

## Running the Scenario

### Command

```bash
sibyl pipeline run risk_graph_analysis \
  --workspace examples/companies/riverbank_finance/config/workspace.yaml \
  --input transaction_file=examples/companies/riverbank_finance/data/transactions/transactions.json \
  --input metric_type=pagerank \
  --input top_n=10
```

### Alternative Metrics

```bash
# Use betweenness centrality (identifies intermediaries)
sibyl pipeline run risk_graph_analysis --input metric_type=betweenness --input top_n=10

# Use degree centrality (identifies most connected nodes)
sibyl pipeline run risk_graph_analysis --input metric_type=degree --input top_n=10
```

## Expected Output

### Pipeline Flow

```
Step 1: load_transactions
  ↓ Reads transactions.json
  ✓ Output: Parsed transaction data (1000 transactions, 10 customers)

Step 2: build_graph
  ↓ Graphiti MCP builds graph
  ✓ Output: GraphArtifact
    - Nodes: 10 customers + counterparties
    - Edges: 1000 transactions (directed, weighted by amount)
    - Graph type: DIRECTED

Step 3: calculate_centrality
  ↓ NetworkX computes PageRank
  ✓ Output: GraphMetricsArtifact
    - Algorithm: "pagerank"
    - Scores: {CUST-1001: 0.045, CUST-1004: 0.125, CUST-1006: 0.180, ...}
    - Ranked nodes: Top 10 by PageRank score

Step 4: rank_customers
  ↓ Extract top N from GraphMetricsArtifact
  ✓ Output: Top 10 ranked customers

Step 5: generate_risk_report
  ↓ LLM analyzes metrics + patterns
  ✓ Output: Risk Assessment Report (see below)
```

### Risk Report Structure

```yaml
risk_assessment_report:
  analysis_date: "2024-11-22"
  metric_used: "pagerank"
  total_customers_analyzed: 10
  total_transactions: 1000
  time_period: "2024-10-01 to 2024-10-31"

  top_risk_customers:
    - rank: 1
      customer_id: "CUST-1006"
      pagerank_score: 0.182
      risk_level: "CRITICAL"
      red_flags:
        - "High centrality (hub node)"
        - "Circular transaction pattern with CUST-1007"
        - "10+ bidirectional transactions"
        - "Amount escalation: $3,000 → $6,500"
      pattern_details:
        pattern_type: "Circular Transactions"
        counterparty: "CUST-1007"
        transaction_count: 10
        total_volume: "$48,000"
        frequency: "Every 2-3 days"
      aml_policy_violations:
        - "AML-001: Circular Transactions"
        - "AML-001: High-Risk Counterparties"
      recommended_action: "File SAR, freeze accounts pending investigation"

    - rank: 2
      customer_id: "CUST-1007"
      pagerank_score: 0.175
      risk_level: "CRITICAL"
      red_flags:
        - "High centrality (hub node)"
        - "Circular transaction pattern with CUST-1006"
        - "Isolated cluster (only transacts with CUST-1006)"
      pattern_details:
        pattern_type: "Circular Transactions"
        counterparty: "CUST-1006"
        transaction_count: 10
        total_volume: "$46,000"
      aml_policy_violations:
        - "AML-001: Circular Transactions"
      recommended_action: "File SAR, coordinate with CUST-1006 investigation"

    - rank: 3
      customer_id: "CUST-1010"
      pagerank_score: 0.145
      risk_level: "CRITICAL"
      red_flags:
        - "Velocity abuse: 6 transactions in 60 minutes"
        - "Structuring pattern: 4 transactions $9,000-$9,500"
        - "New account (60 days old)"
        - "High transaction volume vs. expected"
      pattern_details:
        pattern_type: "Structuring + Velocity Abuse"
        structuring_transactions: 4
        amounts: ["$9,000", "$9,500", "$9,300", "$9,500"]
        velocity_incident: "2024-10-03 10:00-10:55 (6 txns)"
      aml_policy_violations:
        - "AML-001: Structuring Detection"
        - "AML-001: Transaction Velocity (exceeds 5/hour limit)"
        - "TXN-003: Velocity Monitoring"
      recommended_action: "File SAR, restrict account, enhanced monitoring"

    - rank: 4
      customer_id: "CUST-1004"
      pagerank_score: 0.125
      risk_level: "HIGH"
      red_flags:
        - "Structuring pattern: 5 transactions $9,000-$9,800"
        - "All cash withdrawals"
        - "Multiple branch locations used"
      pattern_details:
        pattern_type: "Structuring"
        structuring_transactions: 5
        amounts: ["$9,000", "$9,500", "$9,800", "$9,200", "$9,100"]
        time_span: "2 weeks"
      aml_policy_violations:
        - "AML-001: Structuring Detection"
        - "AML-003: CTR Aggregation (total $46,600 in 30 days)"
      recommended_action: "File SAR, enhanced due diligence"

    # ... ranks 5-10 (lower risk)

  graph_statistics:
    total_nodes: 25  # 10 customers + 15 counterparties
    total_edges: 1000
    average_degree: 40
    density: 0.042
    clustering_coefficient: 0.35
    connected_components: 3  # CUST-1006/1007 isolated cluster

  suspicious_clusters:
    - cluster_id: 1
      nodes: ["CUST-1006", "CUST-1007"]
      description: "Isolated high-frequency transaction cluster"
      transaction_count: 20
      total_volume: "$94,000"
      risk_assessment: "CRITICAL - likely money laundering ring"

  centrality_analysis:
    pagerank_distribution:
      mean: 0.040
      std_dev: 0.055
      max: 0.182  # CUST-1006
      min: 0.012
    high_centrality_threshold: 0.100  # 2.5 std devs above mean
    customers_above_threshold: 4  # CUST-1006, 1007, 1010, 1004

  recommended_actions:
    immediate:
      - "File SARs for CUST-1004, CUST-1006, CUST-1007, CUST-1010"
      - "Freeze accounts CUST-1006 and CUST-1007 pending investigation"
      - "Request additional documentation from CUST-1004 and CUST-1010"

    short_term:
      - "Enhanced monitoring for all customers in cluster with CUST-1006/1007"
      - "Review historical transactions for these customers (6-12 months)"
      - "Coordinate with law enforcement if criminal activity suspected"

    long_term:
      - "Adjust velocity monitoring thresholds (currently 5/hour may be too high)"
      - "Implement real-time alerts for circular transaction patterns"
      - "Train staff on structuring indicators"

  compliance_impact:
    sars_to_file: 4
    accounts_to_restrict: 2
    accounts_for_edd: 4
    estimated_investigation_hours: 80
```

## Verification

### GraphArtifact Structure

```python
graph_artifact = GraphArtifact(
    nodes=[
        Node(id="CUST-1001", type="customer", properties={"risk_level": "low"}),
        Node(id="CUST-1004", type="customer", properties={"risk_level": "high"}),
        # ... more customers
    ],
    edges=[
        Edge(source="CUST-1004", target="ATM-BRANCH-01", type="transaction", weight=9000.0),
        Edge(source="CUST-1006", target="CUST-1007", type="transaction", weight=3000.0),
        # ... more transactions
    ],
    graph_type=GraphType.DIRECTED,
    metadata={"source": "graphiti", "transaction_count": 1000}
)

# Convert to NetworkX
nx_graph = graph_artifact.to_networkx()
assert nx_graph.number_of_nodes() >= 10
assert nx_graph.number_of_edges() >= 50
```

### GraphMetricsArtifact Structure

```python
metrics = GraphMetricsArtifact(
    algorithm="pagerank",
    metric_type=MetricType.PAGERANK,
    scores={
        "CUST-1001": 0.045,
        "CUST-1004": 0.125,
        "CUST-1006": 0.182,
        "CUST-1007": 0.175,
        "CUST-1010": 0.145,
        # ...
    },
    ranked_nodes=[
        RankedNode(node_id="CUST-1006", score=0.182, rank=1),
        RankedNode(node_id="CUST-1007", score=0.175, rank=2),
        # ...
    ]
)

# Get top 10
top_10 = metrics.get_top_nodes(n=10)
assert len(top_10) == 10
assert top_10[0].node_id in ["CUST-1006", "CUST-1007"]  # High-risk nodes

# Get specific score
cust_1004_score = metrics.get_node_score("CUST-1004")
assert cust_1004_score > 0.1  # Should be high risk
```

## What's Demonstrated

### 1. Transaction Data → Graph
Shows ingestion of transaction data and construction of directed graph with:
- Customers as nodes
- Transactions as weighted edges
- Metadata preservation

### 2. Graphiti MCP Integration
Demonstrates:
- Building graphs in Graphiti
- Querying nodes and facts
- Converting Graphiti results to GraphArtifact

### 3. NetworkX Analysis
Shows:
- Converting GraphArtifact to NetworkX graph
- Calculating centrality metrics (PageRank, betweenness, degree)
- Creating GraphMetricsArtifact from results

### 4. Cross-MCP Workflow
Complete flow:
- Graphiti (graph construction) → GraphArtifact
- NetworkX (graph metrics) → GraphMetricsArtifact
- LLM (risk analysis) → Report

### 5. Real-World AML Patterns
Detects actual money laundering indicators:
- Structuring (policy AML-001)
- Circular transactions (policy AML-001)
- Velocity abuse (policy TXN-003)
- High centrality = potential hub/mule

## Next Steps

### Try Different Metrics
```bash
# Betweenness finds intermediaries
sibyl pipeline run risk_graph_analysis --input metric_type=betweenness

# Degree finds most active nodes
sibyl pipeline run risk_graph_analysis --input metric_type=degree
```

### Add More Patterns
Edit `transactions.json` to add:
- International wire transfers
- PEP customer transactions
- High-risk jurisdiction transactions

### Build Visualization
```python
import networkx as nx
import matplotlib.pyplot as plt

# Get graph from artifact
nx_graph = graph_artifact.to_networkx()

# Color nodes by risk
node_colors = [metrics.get_node_score(node, 0.01) for node in nx_graph.nodes()]

nx.draw(nx_graph, node_color=node_colors, with_labels=True, cmap='YlOrRd')
plt.savefig('risk_graph.png')
```

---

**Related Scenarios**:
- Scenario 1: Code Compliance Check (AST analysis)
- Scenario 3: Policy Explainer (RAG Q&A)

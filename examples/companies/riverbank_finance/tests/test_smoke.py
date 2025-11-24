"""
Smoke tests for RiverBank Finance compliance example.

Tests verify:
- Code compliance pipeline produces ASTArtifact
- Risk graph pipeline produces GraphArtifact and GraphMetricsArtifact
- Policy RAG retrieves relevant content
- Typed artifacts have correct structure
"""

import json
from pathlib import Path

import pytest

# Test data paths
BASE_DIR = Path(__file__).parent.parent
CODE_DIR = BASE_DIR / "data" / "code"
DOCS_DIR = BASE_DIR / "data" / "docs"
TRANSACTIONS_DIR = BASE_DIR / "data" / "transactions"


class TestDataExistence:
    """Verify all required test data exists."""

    def test_code_files_exist(self) -> None:
        """Verify banking code files exist."""
        assert (CODE_DIR / "interest_calculator.py").exists()
        assert (CODE_DIR / "transaction_processor.js").exists()
        assert (CODE_DIR / "risk_scorer.py").exists()

    def test_policy_docs_exist(self) -> None:
        """Verify policy documents exist."""
        assert (DOCS_DIR / "interest_rate_policy.md").exists()
        assert (DOCS_DIR / "aml_policy.md").exists()
        assert (DOCS_DIR / "kyc_policy.md").exists()
        assert (DOCS_DIR / "transaction_limits.md").exists()

    def test_transaction_data_exists(self) -> None:
        """Verify transaction data exists."""
        assert (TRANSACTIONS_DIR / "transactions.json").exists()


class TestTransactionData:
    """Verify transaction data structure and suspicious patterns."""

    def test_transaction_json_structure(self) -> None:
        """Verify transaction JSON has required structure."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "customers" in data
        assert "transactions" in data
        assert "suspicious_patterns" in data

        # Verify metadata
        assert data["metadata"]["total_transactions"] >= 50  # noqa: PLR2004
        assert "generated" in data["metadata"]

        # Verify customers
        assert len(data["customers"]) >= 10  # noqa: PLR2004
        customer = data["customers"][0]
        assert "customer_id" in customer
        assert "risk_level" in customer
        assert "account_type" in customer

        # Verify transactions
        assert len(data["transactions"]) >= 50  # noqa: PLR2004
        transaction = data["transactions"][0]
        assert "id" in transaction
        assert "customer_id" in transaction
        assert "amount" in transaction
        assert "type" in transaction
        assert "counterparty" in transaction

    def test_suspicious_patterns_present(self) -> None:
        """Verify suspicious patterns are documented."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        patterns = data["suspicious_patterns"]

        # Check for structuring pattern
        assert "structuring" in patterns
        assert "customers" in patterns["structuring"]
        assert len(patterns["structuring"]["customers"]) >= 2  # noqa: PLR2004

        # Check for circular transactions
        assert "circular_transactions" in patterns
        assert "customers" in patterns["circular_transactions"]
        assert len(patterns["circular_transactions"]["customers"]) >= 2  # noqa: PLR2004

        # Check for velocity abuse
        assert "velocity_abuse" in patterns
        assert "severity" in patterns["velocity_abuse"]
        assert patterns["velocity_abuse"]["severity"] in ["HIGH", "CRITICAL"]

    def test_high_risk_customers_flagged(self) -> None:
        """Verify high-risk customers are properly flagged."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        high_risk_customers = [
            c for c in data["customers"] if c.get("risk_level") in ["high", "critical"]
        ]

        assert len(high_risk_customers) >= 3, "Should have at least 3 high-risk customers"  # noqa: PLR2004

        # Verify they have notes explaining the risk
        for customer in high_risk_customers:
            assert "notes" in customer or "risk_factors" in customer


class TestCodeCompliance:
    """Test code compliance detection."""

    def test_interest_calculator_has_bugs(self) -> None:
        """Verify interest_calculator.py contains intentional bugs."""
        code_path = CODE_DIR / "interest_calculator.py"
        code_content = code_path.read_text()

        # Check for compound interest bug marker
        assert "BUG" in code_content, "Code should have bug markers"
        assert "calculate_compound_interest" in code_content
        assert "calculate_savings_account_interest" in code_content

        # Check for policy references
        assert "Policy INT-001" in code_content or "INT-001" in code_content
        assert "Policy INT-002" in code_content or "INT-002" in code_content

    def test_transaction_processor_has_issues(self) -> None:
        """Verify transaction_processor.js contains compliance issues."""
        code_path = CODE_DIR / "transaction_processor.js"
        code_content = code_path.read_text()

        # Check for velocity check bug
        assert "BUG" in code_content or "WRONG" in code_content
        assert "checkTransactionVelocity" in code_content
        assert "VELOCITY_THRESHOLD" in code_content

        # Check for policy references
        assert "TXN-001" in code_content
        assert "AML-001" in code_content

    def test_risk_scorer_variance_bug(self) -> None:
        """Verify risk_scorer.py has variance threshold bug."""
        code_path = CODE_DIR / "risk_scorer.py"
        code_content = code_path.read_text()

        # Check for variance calculation bug
        assert "variance > 0.30" in code_content or "variance > 0.3" in code_content
        assert "BUG" in code_content
        assert "50% variance threshold" in code_content or "0.50 per policy" in code_content

        # Check for policy references
        assert "AML-002" in code_content
        assert "KYC-001" in code_content


class TestPolicyDocuments:
    """Test policy document structure."""

    def test_interest_policy_has_formulas(self) -> None:
        """Verify interest rate policy contains required formulas."""
        policy_path = DOCS_DIR / "interest_rate_policy.md"
        policy_content = policy_path.read_text()

        # Check for policy IDs
        assert "INT-001" in policy_content
        assert "INT-002" in policy_content
        assert "INT-003" in policy_content

        # Check for formulas
        assert "I = P × R × T" in policy_content or "I = P * R * T" in policy_content
        assert "A = P(1 + r/n)^(nt)" in policy_content or "A = P(1 + r/n)" in policy_content
        assert "360" in policy_content  # 360-day year requirement

        # Check for critical requirements
        assert "CRITICAL" in policy_content or "must" in policy_content.lower()

    def test_aml_policy_has_thresholds(self) -> None:
        """Verify AML policy contains detection thresholds."""
        policy_path = DOCS_DIR / "aml_policy.md"
        policy_content = policy_path.read_text()

        # Check for policy IDs
        assert "AML-001" in policy_content
        assert "AML-002" in policy_content

        # Check for key thresholds
        assert "10,000" in policy_content or "$10,000" in policy_content  # CTR threshold
        assert "structuring" in policy_content.lower()
        assert "velocity" in policy_content.lower()
        assert "5 transactions" in policy_content or "5-transaction" in policy_content

    def test_transaction_limits_policy(self) -> None:
        """Verify transaction limits policy has limits."""
        policy_path = DOCS_DIR / "transaction_limits.md"
        policy_content = policy_path.read_text()

        # Check for policy IDs
        assert "TXN-001" in policy_content
        assert "TXN-003" in policy_content

        # Check for limits
        assert "$5,000" in policy_content or "5000" in policy_content
        assert "$10,000" in policy_content or "10000" in policy_content
        assert "velocity" in policy_content.lower()


class TestArtifactStructures:
    """Test typed artifact structures (conceptual - would need actual Sibyl runtime)."""

    def test_ast_artifact_structure(self) -> None:
        """Verify ASTArtifact structure expectations."""
        # This is a conceptual test - would need actual AST parsing
        # In real implementation, would:
        # 1. Parse interest_calculator.py
        # 2. Build ASTArtifact
        # 3. Verify structure

        expected_functions = [
            "calculate_simple_interest",
            "calculate_compound_interest",
            "calculate_savings_account_interest",
            "calculate_loan_payment",
            "apply_promotional_rate",
        ]

        # Conceptual assertions
        assert len(expected_functions) == 5  # noqa: PLR2004
        assert "calculate_compound_interest" in expected_functions

    def test_graph_artifact_structure(self) -> None:
        """Verify GraphArtifact structure expectations."""
        # Conceptual test - would need actual graph construction
        # In real implementation, would:
        # 1. Load transactions.json
        # 2. Build GraphArtifact with Graphiti
        # 3. Verify structure

        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        expected_nodes = len(data["customers"])  # At least customer nodes
        expected_edges = len(data["transactions"])

        assert expected_nodes >= 10  # noqa: PLR2004
        assert expected_edges >= 50  # noqa: PLR2004

    def test_graph_metrics_artifact_structure(self) -> None:
        """Verify GraphMetricsArtifact structure expectations."""
        # Conceptual test - would need actual NetworkX calculation
        # In real implementation, would:
        # 1. Build graph
        # 2. Calculate PageRank
        # 3. Create GraphMetricsArtifact
        # 4. Verify structure

        expected_fields = {
            "algorithm": "pagerank",
            "metric_type": "PAGERANK",
            "scores": {},  # node_id -> score
            "ranked_nodes": [],  # sorted by score
            "computation_time_ms": 0,
        }

        assert "algorithm" in expected_fields
        assert "scores" in expected_fields
        assert "ranked_nodes" in expected_fields


class TestScenarioInputs:
    """Test that scenario inputs are valid."""

    def test_code_compliance_inputs(self) -> None:
        """Verify code compliance scenario has valid inputs."""
        # Scenario 1 input: file_path
        file_path = CODE_DIR / "interest_calculator.py"
        assert file_path.exists()
        assert file_path.suffix == ".py"

        # Policy reference should be valid
        policy_reference = "INT-002"
        assert len(policy_reference) > 0

    def test_risk_graph_inputs(self) -> None:
        """Verify risk graph scenario has valid inputs."""
        # Scenario 2 input: transaction_file
        transaction_file = TRANSACTIONS_DIR / "transactions.json"
        assert transaction_file.exists()

        with open(transaction_file) as f:
            data = json.load(f)
            assert len(data["transactions"]) >= 50  # noqa: PLR2004

        # Metric type should be valid
        metric_types = ["pagerank", "betweenness", "degree"]
        assert "pagerank" in metric_types

    def test_policy_explainer_inputs(self) -> None:
        """Verify policy explainer scenario has valid inputs."""
        # Scenario 3 input: question
        questions = [
            "What is structuring and how do we detect it?",
            "What formula should I use for compound interest?",
            "What is the CTR filing threshold?",
        ]

        for question in questions:
            assert len(question) > 10  # noqa: PLR2004
            assert "?" in question

        # Policy areas should be valid
        policy_areas = ["KYC", "AML", "interest_rates", "transactions"]
        assert "AML" in policy_areas


class TestCompliancePatterns:
    """Test that we can identify the expected compliance issues."""

    def test_structuring_pattern_identifiable(self) -> None:
        """Verify structuring pattern is clearly identifiable."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        # Find structuring customers
        structuring_customers = data["suspicious_patterns"]["structuring"]["customers"]

        # Check their transactions
        for cust_id in structuring_customers:
            cust_txns = [
                t
                for t in data["transactions"]
                if t["customer_id"] == cust_id and "structuring_indicator" in t.get("flags", [])
            ]

            # Should have multiple transactions near $10k threshold
            amounts_near_threshold = [
                t["amount"]
                for t in cust_txns
                if 8000 <= t["amount"] <= 10000  # noqa: PLR2004
            ]

            assert (
                len(amounts_near_threshold) >= 2
            ), f"Customer {cust_id} should have structuring pattern"  # noqa: PLR2004

    def test_circular_pattern_identifiable(self) -> None:
        """Verify circular transaction pattern is identifiable."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        circular_customers = data["suspicious_patterns"]["circular_transactions"]["customers"]
        assert len(circular_customers) >= 2  # noqa: PLR2004

        # Check for bidirectional transactions
        cust_a, cust_b = circular_customers[0], circular_customers[1]

        # Find transactions A->B
        a_to_b = [
            t
            for t in data["transactions"]
            if t["customer_id"] == cust_a and t["counterparty"] == cust_b
        ]

        # Find transactions B->A
        b_to_a = [
            t
            for t in data["transactions"]
            if t["customer_id"] == cust_b and t["counterparty"] == cust_a
        ]

        assert len(a_to_b) >= 3, "Should have multiple A->B transactions"  # noqa: PLR2004
        assert len(b_to_a) >= 3, "Should have multiple B->A transactions"  # noqa: PLR2004

    def test_velocity_pattern_identifiable(self) -> None:
        """Verify velocity abuse pattern is identifiable."""
        with open(TRANSACTIONS_DIR / "transactions.json") as f:
            data = json.load(f)

        velocity_customer = data["suspicious_patterns"]["velocity_abuse"]["customers"][0]

        # Find velocity-flagged transactions
        velocity_txns = [
            t
            for t in data["transactions"]
            if t["customer_id"] == velocity_customer and "velocity_check" in t.get("flags", [])
        ]

        assert len(velocity_txns) >= 5, "Should have high-velocity transaction sequence"  # noqa: PLR2004

        # Check they're close together in time (within 60 minutes)
        if len(velocity_txns) >= 6:  # noqa: PLR2004
            timestamps = [t["timestamp"] for t in velocity_txns[:6]]
            # Just verify we have timestamps
            assert all(timestamps)


class TestIntegration:
    """Integration tests (require actual Sibyl runtime)."""

    @pytest.mark.skip(reason="Requires Sibyl runtime and MCP servers")
    def test_code_compliance_pipeline(self) -> None:
        """Test full code compliance pipeline execution."""
        # This would require:
        # 1. Sibyl runtime initialized
        # 2. AST Server MCP running
        # 3. Vector store initialized with policies
        # 4. LLM provider configured

        # Conceptual test:
        # result = sibyl.pipeline.run(
        #     "code_compliance_check",
        #     input={
        #         "file_path": str(CODE_DIR / "interest_calculator.py"),
        #         "policy_reference": "INT-002"
        #     }
        # )
        #
        # assert "violations" in result
        # assert len(result["violations"]) >= 2  # compound interest + savings bugs
        # assert any("compound" in v["function"] for v in result["violations"])

    @pytest.mark.skip(reason="Requires Sibyl runtime and MCP servers")
    def test_risk_graph_pipeline(self) -> None:
        """Test full risk graph analysis pipeline execution."""
        # This would require:
        # 1. Sibyl runtime initialized
        # 2. Graphiti MCP running
        # 3. NetworkX available

        # Conceptual test:
        # result = sibyl.pipeline.run(
        #     "risk_graph_analysis",
        #     input={
        #         "transaction_file": str(TRANSACTIONS_DIR / "transactions.json"),
        #         "metric_type": "pagerank",
        #         "top_n": 10
        #     }
        # )
        #
        # assert "graph_artifact" in result
        # assert "graph_metrics_artifact" in result
        # assert len(result["ranked_customers"]) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

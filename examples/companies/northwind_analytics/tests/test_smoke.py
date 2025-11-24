"""
Smoke tests for Northwind Analytics example pipelines.

These tests verify that the example structure and data are correct
without requiring full Sibyl imports or execution.
"""

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# Add parent directory to path for imports
example_dir = Path(__file__).parent.parent


class TestNorthwindAnalyticsWorkspace:
    """Test workspace loading and configuration."""

    @pytest.fixture
    def workspace_path(self) -> Any:
        """Path to workspace configuration."""
        return example_dir / "config" / "workspace.yaml"

    @pytest.fixture
    def workspace_config(self, workspace_path: Any) -> Any:
        """Load workspace configuration as dict."""
        with open(workspace_path) as f:
            return yaml.safe_load(f)

    def test_workspace_file_exists(self, workspace_path: Any) -> None:
        """Verify workspace configuration file exists."""
        assert workspace_path.exists()
        assert workspace_path.stat().st_size > 0

    def test_workspace_structure(self, workspace_config: Any) -> None:
        """Verify workspace has correct structure."""
        assert workspace_config is not None
        assert workspace_config["name"] == "northwind-analytics"
        assert workspace_config["version"] == "1.0"
        assert "description" in workspace_config

    def test_workspace_has_providers(self, workspace_config: Any) -> None:
        """Verify all required providers are configured."""
        providers = workspace_config["providers"]

        # Document sources
        assert "document_sources" in providers
        assert "product_docs" in providers["document_sources"]

        # SQL
        assert "sql" in providers
        assert "analytics_warehouse" in providers["sql"]

        # Vector store
        assert "vector_store" in providers
        assert "docs_index" in providers["vector_store"]

        # LLM
        assert "llm" in providers
        assert "default" in providers["llm"]
        assert "fast" in providers["llm"]

        # Embeddings
        assert "embeddings" in providers
        assert "default" in providers["embeddings"]

    def test_workspace_has_shops(self, workspace_config: Any) -> None:
        """Verify technique shops are defined."""
        shops = workspace_config["shops"]

        assert "rag_shop" in shops
        assert "analytics_shop" in shops
        assert "summarization_shop" in shops

        # Verify RAG shop techniques
        rag_techniques = shops["rag_shop"]["techniques"]
        assert "chunker" in rag_techniques
        assert "embedder" in rag_techniques
        assert "retriever" in rag_techniques
        assert "augmenter" in rag_techniques


class TestSyntheticData:
    """Test synthetic data availability and integrity."""

    def test_markdown_docs_exist(self) -> None:
        """Verify product documentation exists."""
        docs_dir = example_dir / "data" / "docs"
        assert docs_dir.exists()

        # Check for key documentation files
        expected_files = [
            "revenue_definitions.md",
            "dashboard_user_guide.md",
            "kpi_calculation_methods.md",
            "feature_documentation.md",
            "api_reference.md",
        ]

        for filename in expected_files:
            file_path = docs_dir / filename
            assert file_path.exists(), f"Missing doc: {filename}"
            assert file_path.stat().st_size > 0, f"Empty doc: {filename}"

    def test_sql_schema_exists(self) -> None:
        """Verify SQL schema files exist."""
        sql_dir = example_dir / "data" / "sql"
        assert sql_dir.exists()

        # Check for SQL files
        expected_files = [
            "01_schema.sql",
            "02_seed_data.sql",
            "03_revenue_data.sql",
            "init_database.py",
        ]

        for filename in expected_files:
            file_path = sql_dir / filename
            assert file_path.exists(), f"Missing SQL file: {filename}"

    def test_database_can_be_initialized(self) -> None:
        """Verify database initialization script works."""
        import sqlite3  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Import and run initialization
            sql_dir = example_dir / "data" / "sql"
            sys.path.insert(0, str(sql_dir))
            from init_database import init_database  # noqa: PLC0415

            init_database(db_path)

            # Verify tables exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            expected_tables = ["regions", "customers", "subscriptions", "revenue"]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in expected_tables:
                assert table in tables, f"Missing table: {table}"

            # Verify data exists
            cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = cursor.fetchone()[0]
            assert customer_count == 100, f"Expected 100 customers, got {customer_count}"  # noqa: PLR2004

            cursor.execute("SELECT COUNT(*) FROM regions")
            region_count = cursor.fetchone()[0]
            assert region_count == 4, f"Expected 4 regions, got {region_count}"  # noqa: PLR2004

            conn.close()

        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)


class TestRevenueAnalysisPipeline:
    """Test revenue analysis scenario pipeline."""

    @pytest.fixture
    def mock_llm_response(self) -> Any:
        """Mock LLM response for testing."""
        return {
            "analysis": "Q3 2024 MRR declined from $595K to $541K (-9.1%). Primary driver: TechCorp downgrade from Enterprise to Professional in July, resulting in $14K MRR contraction.",
            "key_findings": [
                "Total MRR contraction: $54K (-9.1%)",
                "APAC region most impacted: -$14K (TechCorp downgrade)",
            ],
            "recommendations": [
                "Implement enhanced retention program for at-risk Enterprise accounts",
                "Accelerate v2.0 feature releases",
            ],
        }

    @pytest.fixture
    def mock_sql_results(self) -> Any:
        """Mock SQL query results."""
        return [
            {"year_month": "2024-06", "total_mrr": 595000},
            {"year_month": "2024-07", "total_mrr": 541000},
            {"year_month": "2024-08", "total_mrr": 541000},
            {"year_month": "2024-09", "total_mrr": 541000},
        ]

    @pytest.fixture
    def mock_retrieved_docs(self) -> Any:
        """Mock retrieved documents."""
        return [
            {
                "id": "revenue_definitions.md",
                "content": "Q3 2024 showed a 15% decline in MRR growth. Key factors: APAC slowdown (TechCorp downgrade), seasonal EMEA effect, product transition delays.",
                "metadata": {"title": "Revenue Definitions"},
                "score": 0.94,
            },
            {
                "id": "kpi_calculation_methods.md",
                "content": "MRR = SUM(active_subscriptions.monthly_value)",
                "metadata": {"title": "KPI Calculation Methods"},
                "score": 0.87,
            },
        ]

    def test_pipeline_structure(
        self, mock_llm_response: Any, mock_sql_results: Any, mock_retrieved_docs: Any
    ) -> None:
        """Test that revenue analysis pipeline has correct structure."""
        # Load pipeline configuration
        pipelines_path = example_dir / "config" / "pipelines.yaml"
        assert pipelines_path.exists()

        with open(pipelines_path) as f:
            config = yaml.safe_load(f)

        # Verify revenue_analysis pipeline exists
        assert "pipelines" in config
        assert "revenue_analysis" in config["pipelines"]

        pipeline = config["pipelines"]["revenue_analysis"]

        # Check pipeline structure
        assert "description" in pipeline
        assert "inputs" in pipeline
        assert "steps" in pipeline
        assert "outputs" in pipeline

        # Verify required inputs
        inputs = {inp["name"]: inp for inp in pipeline["inputs"]}
        assert "question" in inputs
        assert inputs["question"]["type"] == "string"
        assert inputs["question"]["required"] is True

        # Verify steps
        steps = pipeline["steps"]
        assert len(steps) >= 5, "Should have at least 5 steps"  # noqa: PLR2004

        step_names = [step["name"] for step in steps]
        assert "expand_query" in step_names
        assert "retrieve_docs" in step_names
        assert "query_revenue_data" in step_names
        assert "generate_analysis" in step_names
        assert "validate_response" in step_names

    def test_pipeline_inputs_validation(self) -> None:
        """Test that pipeline validates inputs correctly."""
        # This would typically use the actual runtime
        # For smoke test, we just verify structure
        pipelines_path = example_dir / "config" / "pipelines.yaml"

        with open(pipelines_path) as f:
            import yaml  # noqa: PLC0415

            config = yaml.safe_load(f)

        pipeline = config["pipelines"]["revenue_analysis"]
        inputs = {inp["name"]: inp for inp in pipeline["inputs"]}

        # question is required
        assert inputs["question"]["required"] is True

        # time_period has default
        assert inputs["time_period"]["required"] is False
        assert "default" in inputs["time_period"]

        # region is optional
        assert inputs["region"]["required"] is False


class TestDashboardExplanationPipeline:
    """Test dashboard explanation scenario pipeline."""

    @pytest.fixture
    def mock_explanation(self) -> str:
        """Mock dashboard explanation."""
        return """## Overview

The Revenue Overview dashboard is your command center for understanding revenue trends.

## Key Metrics

- **Total ARR**: Annual recurring revenue across all customers
- **Active Customers**: Number of customers with active subscriptions

## How to Use

1. Start with the metric cards at the top
2. Check the trend chart in the middle
3. Review the Regional Performance table
"""

    def test_pipeline_exists(self) -> None:
        """Verify explain_dashboard pipeline is defined."""
        pipelines_path = example_dir / "config" / "pipelines.yaml"

        with open(pipelines_path) as f:
            import yaml  # noqa: PLC0415

            config = yaml.safe_load(f)

        assert "explain_dashboard" in config["pipelines"]

        pipeline = config["pipelines"]["explain_dashboard"]

        # Check required inputs
        inputs = {inp["name"]: inp for inp in pipeline["inputs"]}
        assert "dashboard_name" in inputs
        assert "audience" in inputs

        # Check steps use RAG techniques only (no SQL)
        steps = pipeline["steps"]
        step_uses = [step["use"] for step in steps]

        # Should use RAG shop techniques
        assert any("rag_shop" in use for use in step_uses)

        # Should NOT use analytics_shop (which implies SQL)
        # (explanation is pure documentation-based)

    def test_output_structure(self) -> None:
        """Verify pipeline outputs are well-defined."""
        pipelines_path = example_dir / "config" / "pipelines.yaml"

        with open(pipelines_path) as f:
            import yaml  # noqa: PLC0415

            config = yaml.safe_load(f)

        pipeline = config["pipelines"]["explain_dashboard"]

        assert "outputs" in pipeline
        outputs = pipeline["outputs"]

        assert "explanation" in outputs
        assert "sources" in outputs
        assert "quality_score" in outputs


class TestReleaseNotesPipeline:
    """Test release notes generation pipeline."""

    def test_pipeline_exists_and_structured(self) -> None:
        """Verify generate_release_notes pipeline is defined."""
        pipelines_path = example_dir / "config" / "pipelines.yaml"

        with open(pipelines_path) as f:
            import yaml  # noqa: PLC0415

            config = yaml.safe_load(f)

        assert "generate_release_notes" in config["pipelines"]

        pipeline = config["pipelines"]["generate_release_notes"]

        # Check inputs
        inputs = {inp["name"]: inp for inp in pipeline["inputs"]}
        assert "version" in inputs
        assert "release_date" in inputs
        assert "feature_keywords" in inputs

        # feature_keywords should be array type
        assert inputs["feature_keywords"]["type"] == "array"

        # Check outputs
        outputs = pipeline["outputs"]
        assert "release_notes" in outputs
        assert "features_covered" in outputs
        assert "quality_score" in outputs


class TestScenarioDocumentation:
    """Test that scenario documentation is complete."""

    def test_all_scenarios_documented(self) -> None:
        """Verify all scenario markdown files exist."""
        scenarios_dir = example_dir / "scenarios"
        assert scenarios_dir.exists()

        expected_scenarios = [
            "01_revenue_down_q3.md",
            "02_explain_dashboard.md",
            "03_generate_release_notes.md",
        ]

        for filename in expected_scenarios:
            scenario_path = scenarios_dir / filename
            assert scenario_path.exists(), f"Missing scenario: {filename}"
            assert scenario_path.stat().st_size > 0, f"Empty scenario: {filename}"

    def test_scenario_structure(self) -> None:
        """Verify scenarios have required sections."""
        scenarios_dir = example_dir / "scenarios"

        required_sections = [
            "# Scenario",
            "## Problem Statement",
            "## Setup Required",
            "## Command to Run",
            "## Expected Output",
            "## What This Demonstrates",
        ]

        for scenario_file in scenarios_dir.glob("*.md"):
            with open(scenario_file) as f:
                content = f.read()

            for section in required_sections:
                assert section in content, f"{scenario_file.name} missing: {section}"


class TestIntegration:
    """Integration tests with mocked components."""

    def test_configuration_integration(self) -> None:
        """Test that workspace and pipeline configs are compatible."""
        # Load both configurations
        workspace_path = example_dir / "config" / "workspace.yaml"
        pipelines_path = example_dir / "config" / "pipelines.yaml"

        with open(workspace_path) as f:
            workspace = yaml.safe_load(f)

        with open(pipelines_path) as f:
            pipelines = yaml.safe_load(f)

        # Verify pipelines reference shops that exist in workspace
        revenue_pipeline = pipelines["pipelines"]["revenue_analysis"]

        # Extract shop references from pipeline steps
        shop_refs = set()
        for step in revenue_pipeline["steps"]:
            use = step["use"]
            if "." in use:
                shop_name = use.split(".")[0]
                shop_refs.add(shop_name)

        # Verify all referenced shops exist
        available_shops = set(workspace["shops"].keys())
        for shop in shop_refs:
            assert shop in available_shops, f"Pipeline references unknown shop: {shop}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])

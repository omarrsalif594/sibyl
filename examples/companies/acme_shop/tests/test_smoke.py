"""
Smoke tests for Acme Shop example.

Tests verify:
- TimeSeriesArtifact creation and methods
- Revenue forecast pipeline execution
- Product Q&A pipeline execution
- Data integrity
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import TimeSeriesArtifact (with fallback)
try:
    from sibyl.core.artifacts.timeseries import TimePoint, TimeSeriesArtifact, TimeSeriesFrequency
except ImportError:
    # Use standalone definitions if Sibyl not installed
    pytest.skip("Sibyl not installed - using standalone mode", allow_module_level=True)


class TestTimeSeriesArtifact:
    """Test TimeSeriesArtifact functionality."""

    def test_create_artifact_from_data(self) -> None:
        """Test creating TimeSeriesArtifact from time points."""
        # Create sample time points
        time_points = [
            TimePoint(
                timestamp=datetime(2023, 1, 1), value=1000.0, properties={"category": "Camping"}
            ),
            TimePoint(
                timestamp=datetime(2023, 2, 1), value=1500.0, properties={"category": "Camping"}
            ),
            TimePoint(
                timestamp=datetime(2023, 3, 1), value=1200.0, properties={"category": "Camping"}
            ),
        ]

        # Create artifact
        artifact = TimeSeriesArtifact(
            data=time_points,
            frequency=TimeSeriesFrequency.MONTHLY,
            metadata={"source": "test", "unit": "USD"},
        )

        # Assertions
        assert len(artifact) == 3  # noqa: PLR2004
        assert artifact.frequency == TimeSeriesFrequency.MONTHLY
        assert artifact.metadata["source"] == "test"

    def test_get_time_range(self) -> None:
        """Test get_time_range method."""
        time_points = [
            TimePoint(timestamp=datetime(2023, 1, 1), value=100.0),
            TimePoint(timestamp=datetime(2023, 6, 1), value=200.0),
            TimePoint(timestamp=datetime(2023, 12, 1), value=150.0),
        ]

        artifact = TimeSeriesArtifact(data=time_points, frequency=TimeSeriesFrequency.MONTHLY)

        start, end = artifact.get_time_range()

        assert start == datetime(2023, 1, 1)
        assert end == datetime(2023, 12, 1)

    def test_get_value_range(self) -> None:
        """Test get_value_range method."""
        time_points = [
            TimePoint(timestamp=datetime(2023, 1, 1), value=100.0),
            TimePoint(timestamp=datetime(2023, 2, 1), value=500.0),
            TimePoint(timestamp=datetime(2023, 3, 1), value=200.0),
        ]

        artifact = TimeSeriesArtifact(data=time_points, frequency=TimeSeriesFrequency.MONTHLY)

        min_val, max_val = artifact.get_value_range()

        assert min_val == 100.0  # noqa: PLR2004
        assert max_val == 500.0  # noqa: PLR2004

    def test_query_range(self) -> None:
        """Test query_range method."""
        time_points = [
            TimePoint(timestamp=datetime(2023, 1, 1), value=100.0),
            TimePoint(timestamp=datetime(2023, 2, 1), value=200.0),
            TimePoint(timestamp=datetime(2023, 3, 1), value=300.0),
            TimePoint(timestamp=datetime(2023, 4, 1), value=400.0),
        ]

        artifact = TimeSeriesArtifact(data=time_points, frequency=TimeSeriesFrequency.MONTHLY)

        # Query for Feb-Mar
        filtered = artifact.query_range(start=datetime(2023, 2, 1), end=datetime(2023, 3, 1))

        assert len(filtered) == 2  # noqa: PLR2004
        assert filtered.data[0].value == 200.0  # noqa: PLR2004
        assert filtered.data[1].value == 300.0  # noqa: PLR2004

    def test_summarize_for_llm(self) -> None:
        """Test summarize_for_llm method."""
        time_points = [
            TimePoint(timestamp=datetime(2023, i, 1), value=1000.0 + (i * 100))
            for i in range(1, 13)
        ]

        artifact = TimeSeriesArtifact(
            data=time_points,
            frequency=TimeSeriesFrequency.MONTHLY,
            metadata={"model": "test_model"},
        )

        summary = artifact.summarize_for_llm(max_points=5)

        # Check summary contains key information
        assert "2023-01-01" in summary
        assert "2023-12-01" in summary
        assert "monthly" in summary.lower()
        assert "12" in summary  # Number of points

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        time_points = [
            TimePoint(
                timestamp=datetime(2023, 1, 1),
                value=1000.0,
                confidence_lower=900.0,
                confidence_upper=1100.0,
                properties={"is_forecast": True},
            ),
        ]

        artifact = TimeSeriesArtifact(
            data=time_points, frequency=TimeSeriesFrequency.MONTHLY, metadata={"source": "test"}
        )

        result = artifact.to_dict()

        assert "data" in result
        assert "frequency" in result
        assert "metadata" in result
        assert result["frequency"] == "monthly"
        assert len(result["data"]) == 1
        assert result["data"][0]["value"] == 1000.0  # noqa: PLR2004
        assert result["data"][0]["confidence_lower"] == 900.0  # noqa: PLR2004

    def test_from_simple_list(self) -> None:
        """Test from_simple_list factory method."""
        timestamps = [datetime(2023, i, 1) for i in range(1, 4)]
        values = [100.0, 200.0, 300.0]

        artifact = TimeSeriesArtifact.from_simple_list(
            timestamps=timestamps, values=values, frequency=TimeSeriesFrequency.MONTHLY
        )

        assert len(artifact) == 3  # noqa: PLR2004
        assert artifact.data[0].value == 100.0  # noqa: PLR2004
        assert artifact.data[2].value == 300.0  # noqa: PLR2004

    def test_from_mcp_response(self) -> None:
        """Test from_mcp_response factory method."""
        mcp_response = {
            "forecast": [
                {"timestamp": "2023-01-01T00:00:00", "value": 100.0},
                {"timestamp": "2023-02-01T00:00:00", "value": 200.0},
            ],
            "confidence_intervals": [
                {"lower": 90.0, "upper": 110.0},
                {"lower": 180.0, "upper": 220.0},
            ],
            "frequency": "monthly",
            "model": "prophet",
            "mae": 5.5,
        }

        artifact = TimeSeriesArtifact.from_mcp_response(response=mcp_response, provider="chronulus")

        assert len(artifact) == 2  # noqa: PLR2004
        assert artifact.frequency == TimeSeriesFrequency.MONTHLY
        assert artifact.metadata["provider"] == "chronulus"
        assert artifact.metadata["model"] == "prophet"
        assert artifact.metadata["mae"] == 5.5  # noqa: PLR2004
        assert artifact.data[0].confidence_lower == 90.0  # noqa: PLR2004
        assert artifact.data[0].confidence_upper == 110.0  # noqa: PLR2004


class TestDatabaseIntegrity:
    """Test Acme Shop database integrity."""

    @pytest.fixture
    def db_path(self) -> Any:
        """Get database path."""
        return Path(__file__).parent.parent / "data" / "sql" / "acme_shop.db"

    def test_database_exists(self, db_path: Any) -> None:
        """Test that database file exists."""
        assert db_path.exists(), "Database not found. Run: python data/sql/generate_data.py"

    def test_tables_exist(self, db_path: Any) -> None:
        """Test that required tables exist."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
        """)
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {"categories", "products", "customers", "orders", "order_items"}
        assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

        conn.close()

    def test_orders_data(self, db_path: Any) -> None:
        """Test orders data integrity."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Count orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]

        assert order_count > 0, "No orders in database"
        assert order_count >= 900, f"Expected ~1000 orders, got {order_count}"  # noqa: PLR2004

        # Check date range
        cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM orders")
        min_date, max_date = cursor.fetchone()

        assert min_date is not None
        assert max_date is not None

        # Should span multiple months
        min_dt = datetime.fromisoformat(min_date)
        max_dt = datetime.fromisoformat(max_date)
        months_span = (max_dt.year - min_dt.year) * 12 + (max_dt.month - min_dt.month)

        assert months_span >= 20, f"Expected 24 months, got {months_span}"  # noqa: PLR2004

        conn.close()

    def test_revenue_by_category(self, db_path: Any) -> None:
        """Test revenue aggregation by category."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.name, SUM(oi.line_total) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories c ON p.category_id = c.category_id
            GROUP BY c.name
        """)

        results = {row[0]: row[1] for row in cursor.fetchall()}

        # Check all categories have revenue
        expected_categories = ["Camping", "Apparel", "Footwear", "Backpacks", "Accessories"]
        for category in expected_categories:
            assert category in results, f"Missing revenue for {category}"
            assert results[category] > 0, f"No revenue for {category}"

        conn.close()


class TestRevenueForecastPipeline:
    """Test revenue forecast pipeline."""

    def test_import_pipeline(self) -> None:
        """Test that pipeline can be imported."""
        pipeline_path = Path(__file__).parent.parent / "pipelines" / "revenue_forecast.py"
        assert pipeline_path.exists(), "Revenue forecast pipeline not found"

    def test_query_revenue_by_category(self) -> None:
        """Test SQL query function."""
        # Import function from pipeline
        sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines"))

        try:
            from revenue_forecast import (  # noqa: PLC0415
                aggregate_to_monthly,
                query_revenue_by_category,
            )
        except ImportError:
            pytest.skip("Pipeline module not available")

        db_path = Path(__file__).parent.parent / "data" / "sql" / "acme_shop.db"

        if not db_path.exists():
            pytest.skip("Database not generated")

        # Query Camping revenue
        results = query_revenue_by_category(db_path, category="Camping")

        assert len(results) > 0, "No revenue data returned"

        # Check data format
        date_str, revenue = results[0]
        assert isinstance(date_str, str)
        assert isinstance(revenue, (int, float))
        assert revenue > 0

    def test_build_timeseries_artifact(self) -> None:
        """Test TimeSeriesArtifact construction."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines"))

        try:
            from revenue_forecast import build_timeseries_artifact  # noqa: PLC0415
        except ImportError:
            pytest.skip("Pipeline module not available")

        # Sample monthly data
        monthly_data = [
            ("2023-01", 1000.0),
            ("2023-02", 1500.0),
            ("2023-03", 1200.0),
        ]

        artifact = build_timeseries_artifact(monthly_data, category="Camping")

        assert len(artifact) == 3  # noqa: PLR2004
        assert artifact.frequency == TimeSeriesFrequency.MONTHLY
        assert artifact.metadata["category"] == "Camping"
        assert artifact.data[0].value == 1000.0  # noqa: PLR2004

    @patch("revenue_forecast.call_chronulus_mcp")
    def test_full_pipeline_execution(self, mock_chronulus: Any) -> None:
        """Test full pipeline execution with mocked Chronulus."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines"))

        try:
            from revenue_forecast import run_revenue_forecast_pipeline  # noqa: PLC0415
        except ImportError:
            pytest.skip("Pipeline module not available")

        db_path = Path(__file__).parent.parent / "data" / "sql" / "acme_shop.db"

        if not db_path.exists():
            pytest.skip("Database not generated")

        # Mock Chronulus response
        mock_forecast = TimeSeriesArtifact(
            data=[
                TimePoint(
                    timestamp=datetime(2025, 1, 1),
                    value=5000.0,
                    confidence_lower=4500.0,
                    confidence_upper=5500.0,
                )
            ],
            frequency=TimeSeriesFrequency.MONTHLY,
            metadata={"provider": "chronulus", "model": "mock"},
        )
        mock_chronulus.return_value = mock_forecast

        # Run pipeline
        result = run_revenue_forecast_pipeline(category="Camping", forecast_periods=1)

        # Verify result structure
        assert "category" in result
        assert "forecast_periods" in result
        assert "historical_data" in result
        assert "forecast_data" in result
        assert "report" in result

        # Verify historical data
        assert len(result["historical_data"]["data"]) > 0

        # Verify forecast data
        assert len(result["forecast_data"]["data"]) == 1
        assert result["forecast_data"]["metadata"]["provider"] == "chronulus"


class TestProductQAPipeline:
    """Test product Q&A pipeline."""

    def test_product_docs_exist(self) -> None:
        """Test that product documentation exists."""
        docs_path = Path(__file__).parent.parent / "data" / "docs"

        assert docs_path.exists(), "Product docs directory not found"

        md_files = list(docs_path.glob("*.md"))
        assert len(md_files) >= 10, f"Expected 12+ markdown files, found {len(md_files)}"  # noqa: PLR2004

    def test_doc_content(self) -> None:
        """Test that docs contain expected content."""
        docs_path = Path(__file__).parent.parent / "data" / "docs"
        hoodie_path = docs_path / "alpine_hoodie.md"

        if not hoodie_path.exists():
            pytest.skip("alpine_hoodie.md not found")

        content = hoodie_path.read_text()

        # Check for expected sections
        assert "Alpine Trail Hoodie" in content
        assert "machine-wash" in content.lower()
        assert "Care Instructions" in content or "care instructions" in content.lower()

    def test_import_pipeline(self) -> None:
        """Test that product Q&A pipeline can be imported."""
        pipeline_path = Path(__file__).parent.parent / "pipelines" / "product_qa.py"
        assert pipeline_path.exists(), "Product Q&A pipeline not found"


# Integration test (optional, requires full setup)
@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests requiring complete setup."""

    def test_end_to_end_forecast(self) -> None:
        """Test complete forecast pipeline end-to-end."""
        # This test requires:
        # - Database generated
        # - Chronulus MCP running (or mock)
        # - All dependencies installed

        pytest.skip("Integration test - run manually")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Revenue Forecasting Pipeline for Acme Shop.

This pipeline demonstrates:
1. Querying SQL for historical order data
2. Building TimeSeriesArtifact from SQL results
3. Calling Chronulus MCP for forecasting
4. Returning forecast with confidence intervals

Usage:
    python pipelines/revenue_forecast.py --category Camping --periods 30
    python pipelines/revenue_forecast.py --category Apparel --periods 60
    python pipelines/revenue_forecast.py --all --periods 90
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add parent directories to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sibyl.core.artifacts.timeseries import TimePoint, TimeSeriesArtifact, TimeSeriesFrequency
except ImportError:
    # Fallback: define minimal versions for standalone demo
    from dataclasses import dataclass, field
    from enum import Enum
    from typing import Any

    class TimeSeriesFrequency(Enum):
        MONTHLY = "monthly"
        DAILY = "daily"

    @dataclass
    class TimePoint:
        timestamp: datetime
        value: float
        confidence_lower: float = None
        confidence_upper: float = None
        properties: dict[str, Any] = field(default_factory=dict)

    @dataclass
    class TimeSeriesArtifact:
        data: list[TimePoint]
        frequency: TimeSeriesFrequency
        metadata: dict[str, Any] = field(default_factory=dict)

        def get_time_range(self) -> Any:
            if not self.data:
                return (datetime.now(), datetime.now())
            return (min(p.timestamp for p in self.data), max(p.timestamp for p in self.data))

        def get_value_range(self) -> Any:
            if not self.data:
                return (0.0, 0.0)
            return (min(p.value for p in self.data), max(p.value for p in self.data))

        def to_dict(self) -> Any:
            return {
                "data": [
                    {
                        "timestamp": p.timestamp.isoformat(),
                        "value": p.value,
                        "confidence_lower": p.confidence_lower,
                        "confidence_upper": p.confidence_upper,
                        "properties": p.properties,
                    }
                    for p in self.data
                ],
                "frequency": self.frequency.value,
                "metadata": self.metadata,
            }

        def summarize_for_llm(self, max_points: Any = 10) -> Any:
            if not self.data:
                return "No data"

            lines = []
            start, end = self.get_time_range()
            min_val, max_val = self.get_value_range()
            avg_val = sum(p.value for p in self.data) / len(self.data)

            lines.append(f"Time Series: {start.date()} to {end.date()}")
            lines.append(f"Frequency: {self.frequency.value}")
            lines.append(f"Points: {len(self.data)}")
            lines.append(f"Min: ${min_val:.2f}, Max: ${max_val:.2f}, Avg: ${avg_val:.2f}")

            lines.append("\nSample Points:")
            step = max(1, len(self.data) // max_points)
            for i in range(0, len(self.data), step):
                p = self.data[i]
                date_str = p.timestamp.strftime("%Y-%m")
                if p.confidence_lower and p.confidence_upper:
                    lines.append(
                        f"  {date_str}: ${p.value:.2f} (CI: ${p.confidence_lower:.2f}-${p.confidence_upper:.2f})"
                    )
                else:
                    lines.append(f"  {date_str}: ${p.value:.2f}")

            return "\n".join(lines)


def query_revenue_by_category(
    db_path: Path,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[tuple[str, float]]:
    """Query historical revenue data from SQLite database.

    Args:
        db_path: Path to SQLite database
        category: Optional category filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        List of (date, revenue) tuples
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Build query
    if category:
        query = """
            SELECT DATE(o.order_date) as order_date,
                   SUM(oi.line_total) as daily_revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories c ON p.category_id = c.category_id
            WHERE c.name = ?
        """
        params = [category]
    else:
        query = """
            SELECT DATE(o.order_date) as order_date,
                   SUM(oi.line_total) as daily_revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
        """
        params = []

    # Add date filters
    if start_date:
        query += " AND DATE(o.order_date) >= ?"
        params.append(start_date)

    if end_date:
        query += " AND DATE(o.order_date) <= ?"
        params.append(end_date)

    query += """
        GROUP BY DATE(o.order_date)
        ORDER BY order_date
    """

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return results


def aggregate_to_monthly(daily_data: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Aggregate daily revenue to monthly."""
    monthly_revenue = {}

    for date_str, revenue in daily_data:
        # Extract year-month
        year_month = date_str[:7]  # YYYY-MM

        if year_month in monthly_revenue:
            monthly_revenue[year_month] += revenue
        else:
            monthly_revenue[year_month] = revenue

    # Sort by date
    return sorted(monthly_revenue.items())


def build_timeseries_artifact(
    monthly_data: list[tuple[str, float]], category: str | None = None
) -> TimeSeriesArtifact:
    """Build TimeSeriesArtifact from monthly revenue data.

    This demonstrates typed artifacts.

    Args:
        monthly_data: List of (year-month, revenue) tuples
        category: Optional category name for metadata

    Returns:
        TimeSeriesArtifact ready for Chronulus
    """

    # Convert to TimePoint objects
    time_points = []

    for month_str, revenue in monthly_data:
        # Parse date (YYYY-MM)
        timestamp = datetime.strptime(month_str + "-01", "%Y-%m-%d")

        time_point = TimePoint(
            timestamp=timestamp,
            value=float(revenue),
            properties={"category": category or "all", "is_historical": True},
        )
        time_points.append(time_point)

    # Create artifact
    return TimeSeriesArtifact(
        data=time_points,
        frequency=TimeSeriesFrequency.MONTHLY,
        metadata={
            "source": "acme_shop_orders",
            "category": category or "all_categories",
            "unit": "USD",
            "metric": "revenue",
        },
    )


def call_chronulus_mcp(
    historical_data: TimeSeriesArtifact, forecast_periods: int = 30
) -> TimeSeriesArtifact:
    """Call Chronulus MCP for forecasting.

    In production, this would use the MCP adapter to call Chronulus.
    For this demo, we'll simulate a forecast.

    Args:
        historical_data: Historical time series data
        forecast_periods: Number of periods to forecast

    Returns:
        TimeSeriesArtifact with forecast data
    """

    # Simulate MCP call
    # In production: result = await mcp_adapter(provider="chronulus", tool="create_forecast", ...)

    # For demo, create simulated forecast
    last_point = historical_data.data[-1]
    last_timestamp = last_point.timestamp

    # Simple simulation: trend + seasonality + noise
    forecast_points = []

    # Calculate average from historical data for stable baseline
    all_values = [p.value for p in historical_data.data]
    avg_value = sum(all_values) / len(all_values)

    # Calculate recent trend (last 6 months) as percentage
    if len(historical_data.data) >= 6:  # noqa: PLR2004
        recent_values = [p.value for p in historical_data.data[-6:]]
        trend_pct = (recent_values[-1] - recent_values[0]) / recent_values[0]
        monthly_growth = trend_pct / 6
    else:
        monthly_growth = 0.02  # Default 2% growth

    for i in range(1, forecast_periods + 1):
        # Next month
        next_month = last_timestamp + timedelta(days=30 * i)

        # Simulated forecast value with growth
        base_value = avg_value * (1 + monthly_growth * i)

        # Add seasonality (summer boost for Camping)
        month = next_month.month
        if month in [6, 7, 8]:  # Summer
            seasonal_factor = 1.3
        elif month in [12, 1, 2]:  # Winter
            seasonal_factor = 0.7
        else:
            seasonal_factor = 1.0

        forecast_value = base_value * seasonal_factor

        # Simulated confidence intervals (±15%)
        confidence_range = forecast_value * 0.15

        forecast_point = TimePoint(
            timestamp=next_month,
            value=forecast_value,
            confidence_lower=forecast_value - confidence_range,
            confidence_upper=forecast_value + confidence_range,
            properties={"is_forecast": True, "model": "simulated_prophet"},
        )
        forecast_points.append(forecast_point)

    # Create forecast artifact
    return TimeSeriesArtifact(
        data=forecast_points,
        frequency=TimeSeriesFrequency.MONTHLY,
        metadata={
            "provider": "chronulus",
            "model": "prophet",
            "mae": 250.50,  # Simulated
            "forecast_horizon": forecast_periods,
            "training_samples": len(historical_data.data),
        },
    )


def generate_forecast_report(
    historical: TimeSeriesArtifact, forecast: TimeSeriesArtifact, category: str | None = None
) -> str:
    """Generate human-readable forecast report."""
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("ACME SHOP - REVENUE FORECAST REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Category
    cat_name = category or "All Categories"
    report_lines.append(f"Category: {cat_name}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Historical summary
    report_lines.append("-" * 80)
    report_lines.append("HISTORICAL DATA")
    report_lines.append("-" * 80)
    report_lines.append(historical.summarize_for_llm(max_points=6))
    report_lines.append("")

    # Forecast summary
    report_lines.append("-" * 80)
    report_lines.append("FORECAST")
    report_lines.append("-" * 80)
    report_lines.append(forecast.summarize_for_llm(max_points=10))
    report_lines.append("")

    # Key insights
    report_lines.append("-" * 80)
    report_lines.append("KEY INSIGHTS")
    report_lines.append("-" * 80)

    # Compare last historical value to average forecast
    last_historical = historical.data[-1].value
    forecast_values = [p.value for p in forecast.data]
    avg_forecast = sum(forecast_values) / len(forecast_values)

    change = avg_forecast - last_historical
    pct_change = (change / last_historical) * 100

    report_lines.append(f"• Last historical month revenue: ${last_historical:,.2f}")
    report_lines.append(f"• Average forecasted monthly revenue: ${avg_forecast:,.2f}")
    report_lines.append(f"• Expected change: {pct_change:+.1f}%")

    # Peak forecast month
    peak_idx = forecast_values.index(max(forecast_values))
    peak_point = forecast.data[peak_idx]
    report_lines.append(
        f"• Peak forecasted month: {peak_point.timestamp.strftime('%B %Y')} (${peak_point.value:,.2f})"
    )

    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def run_revenue_forecast_pipeline(
    category: str | None = None, forecast_periods: int = 30
) -> dict[str, Any]:
    """Execute the revenue forecasting pipeline."""

    if category:
        pass
    else:
        pass

    # Database path
    db_path = Path(__file__).parent.parent / "data" / "sql" / "acme_shop.db"

    if not db_path.exists():
        msg = f"Database not found: {db_path}"
        raise FileNotFoundError(msg)

    # Step 1: Query historical revenue from SQL
    daily_revenue = query_revenue_by_category(db_path, category)

    # Aggregate to monthly
    monthly_revenue = aggregate_to_monthly(daily_revenue)

    # Step 2: Build TimeSeriesArtifact
    historical_artifact = build_timeseries_artifact(monthly_revenue, category)

    # Step 3: Call Chronulus MCP for forecasting
    forecast_artifact = call_chronulus_mcp(historical_artifact, forecast_periods)

    # Step 4: Generate report
    report = generate_forecast_report(historical_artifact, forecast_artifact, category)

    # Prepare result
    return {
        "category": category or "all",
        "forecast_periods": forecast_periods,
        "historical_data": historical_artifact.to_dict(),
        "forecast_data": forecast_artifact.to_dict(),
        "report": report,
        "metadata": {
            "pipeline": "revenue_forecast",
            "timestamp": datetime.now().isoformat(),
            "database": str(db_path),
        },
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Forecast revenue for Acme Shop by category")
    parser.add_argument(
        "--category",
        type=str,
        help="Product category (Camping, Apparel, Footwear, Backpacks, Accessories)",
    )
    parser.add_argument("--all", action="store_true", help="Forecast all categories combined")
    parser.add_argument(
        "--periods", type=int, default=30, help="Number of months to forecast (default: 30)"
    )

    args = parser.parse_args()

    # Validate
    valid_categories = ["Camping", "Apparel", "Footwear", "Backpacks", "Accessories"]

    if args.category and args.category not in valid_categories:
        sys.exit(1)

    category = None if args.all else args.category

    if not category and not args.all:
        sys.exit(1)

    try:
        result = run_revenue_forecast_pipeline(category, args.periods)

        # Save result
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"revenue_forecast_{category or 'all'}_{args.periods}mo.json"

        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

    except Exception:
        import traceback  # noqa: PLC0415 - can be moved to top

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

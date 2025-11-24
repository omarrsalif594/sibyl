"""Time Series Artifact for forecast and temporal data.

This module provides typed artifacts for time-series data from Chronulus and other
forecasting tools. It enables LLM-friendly summarization, DuckDB storage, and
time-range queries.

Example:
    from sibyl.core.artifacts.timeseries import TimeSeriesArtifact

    # Create from Chronulus forecast
    ts = TimeSeriesArtifact.from_mcp_response(
        response={"forecast": [...], "confidence_intervals": [...]},
        provider="chronulus"
    )

    # Summarize for LLM
    summary = ts.summarize_for_llm(max_points=10)
"""

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TimeSeriesFrequency(Enum):
    """Time series data frequency."""

    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    UNKNOWN = "unknown"


@dataclass
class TimePoint:
    """A single point in a time series.

    Attributes:
        timestamp: Point in time (datetime or ISO string)
        value: Measured or predicted value
        confidence_lower: Optional lower bound of confidence interval
        confidence_upper: Optional upper bound of confidence interval
        properties: Additional properties (is_forecast, seasonality, etc.)

    Example:
        point = TimePoint(
            timestamp=datetime(2025, 1, 1),
            value=42.5,
            confidence_lower=40.0,
            confidence_upper=45.0
        )
    """

    timestamp: datetime
    value: float
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeriesArtifact:
    """Artifact for time-series data and forecasts.

    This artifact represents time-series data with optional confidence intervals,
    typically produced by Chronulus or other forecasting tools. It includes
    helpers for LLM summarization, DuckDB storage, and time-range queries.

    Attributes:
        data: List of time points
        frequency: Data frequency (daily, hourly, etc.)
        metadata: Metadata (model, accuracy metrics, etc.)

    Example:
        ts = TimeSeriesArtifact(
            data=[
                TimePoint(datetime(2025, 1, 1), 100.0),
                TimePoint(datetime(2025, 1, 2), 105.0),
            ],
            frequency=TimeSeriesFrequency.DAILY,
            metadata={"model": "prophet", "mae": 2.5}
        )

        # Summarize for LLM
        summary = ts.summarize_for_llm(max_points=5)

        # Query time range
        jan_data = ts.query_range(
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31)
        )
    """

    data: list[TimePoint]
    frequency: TimeSeriesFrequency = TimeSeriesFrequency.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        """Return number of time points."""
        return len(self.data)

    def get_value_range(self) -> tuple[float, float]:
        """Get min and max values in the time series.

        Returns:
            Tuple of (min_value, max_value)

        Example:
            min_val, max_val = ts.get_value_range()
            print(f"Range: {min_val} to {max_val}")
        """
        if not self.data:
            return (0.0, 0.0)

        values = [point.value for point in self.data]
        return (min(values), max(values))

    def get_time_range(self) -> tuple[datetime, datetime]:
        """Get start and end timestamps.

        Returns:
            Tuple of (start_time, end_time)

        Example:
            start, end = ts.get_time_range()
            print(f"Data from {start} to {end}")
        """
        if not self.data:
            now = datetime.now()
            return (now, now)

        timestamps = [point.timestamp for point in self.data]
        return (min(timestamps), max(timestamps))

    def query_range(self, start: datetime, end: datetime) -> "TimeSeriesArtifact":
        """Query time series for a specific time range.

        Args:
            start: Start timestamp (inclusive)
            end: End timestamp (inclusive)

        Returns:
            New TimeSeriesArtifact containing only points in range

        Example:
            # Get January 2025 data
            jan_data = ts.query_range(
                start=datetime(2025, 1, 1),
                end=datetime(2025, 1, 31)
            )
        """
        filtered_data = [point for point in self.data if start <= point.timestamp <= end]

        return TimeSeriesArtifact(
            data=filtered_data,
            frequency=self.frequency,
            metadata={**self.metadata, "query_range": f"{start} to {end}"},
        )

    def summarize_for_llm(self, max_points: int = 10, include_statistics: bool = True) -> str:
        """Generate LLM-friendly summary of the time series.

        Creates a concise text summary suitable for inclusion in LLM prompts,
        including key statistics, trends, and sample points.

        Args:
            max_points: Maximum number of sample points to include
            include_statistics: Whether to include statistical summary

        Returns:
            Formatted string summary

        Example:
            summary = ts.summarize_for_llm(max_points=5)
            llm_prompt = f"Analyze this forecast:\\n{summary}\\nWhat are the risks?"
        """
        if not self.data:
            return "Time series is empty."

        lines = []

        # Basic info
        start_time, end_time = self.get_time_range()
        lines.append("Time Series Summary")
        lines.append(f"Period: {start_time.date()} to {end_time.date()}")
        lines.append(f"Frequency: {self.frequency.value}")
        lines.append(f"Data Points: {len(self.data)}")

        # Statistics
        if include_statistics:
            min_val, max_val = self.get_value_range()
            values = [point.value for point in self.data]
            avg_val = sum(values) / len(values)

            lines.append("\nStatistics:")
            lines.append(f"  Min: {min_val:.2f}")
            lines.append(f"  Max: {max_val:.2f}")
            lines.append(f"  Average: {avg_val:.2f}")

            # Trend detection
            if len(values) >= 2:
                start_val = values[0]
                end_val = values[-1]
                change = end_val - start_val
                pct_change = (change / start_val * 100) if start_val != 0 else 0
                trend = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
                lines.append(f"  Trend: {trend} ({pct_change:+.1f}% change)")

        # Sample points (evenly distributed)
        if self.data:
            lines.append(
                f"\nSample Points (showing {min(max_points, len(self.data))} of {len(self.data)}):"
            )

            # Calculate step to evenly distribute sample points
            if len(self.data) <= max_points:
                sample_indices = range(len(self.data))
            else:
                step = len(self.data) / max_points
                sample_indices = [int(i * step) for i in range(max_points)]

            for idx in sample_indices:
                point = self.data[idx]
                timestamp_str = point.timestamp.strftime("%Y-%m-%d %H:%M")
                value_str = f"{point.value:.2f}"

                if point.confidence_lower is not None and point.confidence_upper is not None:
                    lines.append(
                        f"  {timestamp_str}: {value_str} "
                        f"(CI: [{point.confidence_lower:.2f}, {point.confidence_upper:.2f}])"
                    )
                else:
                    lines.append(f"  {timestamp_str}: {value_str}")

        # Add metadata
        if self.metadata:
            model = self.metadata.get("model", "")
            if model:
                lines.append(f"\nModel: {model}")

            # Include accuracy metrics if present
            for metric in ["mae", "mse", "rmse", "mape"]:
                if metric in self.metadata:
                    lines.append(f"  {metric.upper()}: {self.metadata[metric]:.4f}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary.

        Returns:
            Dictionary representation of the artifact

        Example:
            data = ts.to_dict()
            json.dumps(data, default=str)
        """
        return {
            "data": [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "confidence_lower": point.confidence_lower,
                    "confidence_upper": point.confidence_upper,
                    "properties": point.properties,
                }
                for point in self.data
            ],
            "frequency": self.frequency.value,
            "metadata": self.metadata,
        }

    def to_duckdb_compatible(self) -> list[dict[str, Any]]:
        """Convert to DuckDB-compatible format.

        Returns time series data as a list of dictionaries suitable for
        insertion into DuckDB tables or for conversion to pandas DataFrame.

        Returns:
            List of dictionaries with flat structure

        Example:
            # Save to DuckDB
            import duckdb

            conn = duckdb.connect("timeseries.db")
            rows = ts.to_duckdb_compatible()

            conn.execute(
                "CREATE TABLE IF NOT EXISTS forecasts "
                "(timestamp TIMESTAMP, value DOUBLE, "
                "confidence_lower DOUBLE, confidence_upper DOUBLE)"
            )

            conn.executemany(
                "INSERT INTO forecasts VALUES (?, ?, ?, ?)",
                [(r["timestamp"], r["value"], r["confidence_lower"], r["confidence_upper"])
                 for r in rows]
            )
        """
        rows = []
        for point in self.data:
            row = {
                "timestamp": point.timestamp,
                "value": point.value,
                "confidence_lower": point.confidence_lower,
                "confidence_upper": point.confidence_upper,
            }
            # Flatten properties into the row
            for key, value in point.properties.items():
                # Avoid key conflicts
                prop_key = f"prop_{key}" if key in row else key
                row[prop_key] = value

            rows.append(row)

        return rows

    @classmethod
    def from_mcp_response(
        cls, response: dict[str, Any], provider: str = "chronulus"
    ) -> "TimeSeriesArtifact":
        """Create TimeSeriesArtifact from MCP response.

        This factory method handles various response formats from time-series
        MCP tools like Chronulus, normalizing them to a standard artifact structure.

        Args:
            response: Raw response dictionary from MCP forecasting tool
            provider: Forecasting provider name (default "chronulus")

        Returns:
            TimeSeriesArtifact instance

        Example:
            # From Chronulus forecast
            mcp_result = await mcp_adapter(
                provider="chronulus",
                tool="forecast",
                params={"series": historical_data, "periods": 30}
            )

            ts = TimeSeriesArtifact.from_mcp_response(
                mcp_result,
                provider="chronulus"
            )

        Note:
            Expected response format:
            {
                "forecast": [
                    {"timestamp": "2025-01-01T00:00:00", "value": 100.0},
                    {"timestamp": "2025-01-02T00:00:00", "value": 105.0}
                ],
                "confidence_intervals": [
                    {"lower": 95.0, "upper": 105.0},
                    {"lower": 100.0, "upper": 110.0}
                ],
                "frequency": "daily",
                "model": "prophet",
                "mae": 2.5
            }
        """
        # Extract time series data
        data_points = []

        # Try different field names for the main data
        raw_data = response.get("forecast", response.get("data", response.get("series", [])))
        if not isinstance(raw_data, list):
            raw_data = []

        # Extract confidence intervals if present
        confidence_intervals = response.get("confidence_intervals", [])
        if not isinstance(confidence_intervals, list):
            confidence_intervals = []

        # Parse time points
        for i, point_data in enumerate(raw_data):
            # Parse timestamp
            timestamp_str = point_data.get(
                "timestamp", point_data.get("date", point_data.get("time"))
            )
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(str(timestamp_str).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    # Fallback to current time + offset
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Parse value
            value = float(point_data.get("value", point_data.get("y", 0.0)))

            # Parse confidence intervals
            confidence_lower = None
            confidence_upper = None
            if i < len(confidence_intervals):
                ci = confidence_intervals[i]
                confidence_lower = ci.get("lower", ci.get("lower_bound"))
                confidence_upper = ci.get("upper", ci.get("upper_bound"))

                if confidence_lower is not None:
                    confidence_lower = float(confidence_lower)
                if confidence_upper is not None:
                    confidence_upper = float(confidence_upper)

            # Extract additional properties
            properties = {}
            for key in ["is_forecast", "seasonality", "trend", "anomaly"]:
                if key in point_data:
                    properties[key] = point_data[key]

            data_points.append(
                TimePoint(
                    timestamp=timestamp,
                    value=value,
                    confidence_lower=confidence_lower,
                    confidence_upper=confidence_upper,
                    properties=properties,
                )
            )

        # Parse frequency
        frequency_str = response.get("frequency", response.get("freq", "unknown")).lower()
        frequency_mapping = {
            "minute": TimeSeriesFrequency.MINUTE,
            "min": TimeSeriesFrequency.MINUTE,
            "hourly": TimeSeriesFrequency.HOURLY,
            "hour": TimeSeriesFrequency.HOURLY,
            "h": TimeSeriesFrequency.HOURLY,
            "daily": TimeSeriesFrequency.DAILY,
            "day": TimeSeriesFrequency.DAILY,
            "d": TimeSeriesFrequency.DAILY,
            "weekly": TimeSeriesFrequency.WEEKLY,
            "week": TimeSeriesFrequency.WEEKLY,
            "w": TimeSeriesFrequency.WEEKLY,
            "monthly": TimeSeriesFrequency.MONTHLY,
            "month": TimeSeriesFrequency.MONTHLY,
            "m": TimeSeriesFrequency.MONTHLY,
            "quarterly": TimeSeriesFrequency.QUARTERLY,
            "quarter": TimeSeriesFrequency.QUARTERLY,
            "q": TimeSeriesFrequency.QUARTERLY,
            "yearly": TimeSeriesFrequency.YEARLY,
            "year": TimeSeriesFrequency.YEARLY,
            "y": TimeSeriesFrequency.YEARLY,
        }
        frequency = frequency_mapping.get(frequency_str, TimeSeriesFrequency.UNKNOWN)

        # Extract metadata
        metadata = {
            "provider": provider,
        }

        # Include model information if present
        for key in ["model", "algorithm", "method"]:
            if key in response:
                metadata[key] = response[key]

        # Include accuracy metrics if present
        for key in ["mae", "mse", "rmse", "mape", "accuracy"]:
            if key in response:
                with contextlib.suppress(TypeError, ValueError):
                    metadata[key] = float(response[key])

        # Include other metadata
        for key in ["forecast_horizon", "training_samples", "version"]:
            if key in response:
                metadata[key] = response[key]

        return cls(data=data_points, frequency=frequency, metadata=metadata)

    @classmethod
    def from_simple_list(
        cls,
        timestamps: list[datetime],
        values: list[float],
        frequency: TimeSeriesFrequency = TimeSeriesFrequency.UNKNOWN,
        confidence_intervals: list[tuple[float, float]] | None = None,
    ) -> "TimeSeriesArtifact":
        """Create TimeSeriesArtifact from simple lists.

        Convenience factory method for when you have separate lists of
        timestamps and values.

        Args:
            timestamps: List of timestamps
            values: List of values
            frequency: Data frequency
            confidence_intervals: Optional list of (lower, upper) tuples

        Returns:
            TimeSeriesArtifact instance

        Example:
            ts = TimeSeriesArtifact.from_simple_list(
                timestamps=[datetime(2025, 1, i) for i in range(1, 11)],
                values=[100.0 + i for i in range(10)],
                frequency=TimeSeriesFrequency.DAILY
            )
        """
        if len(timestamps) != len(values):
            msg = "timestamps and values must have the same length"
            raise ValueError(msg)

        data_points = []
        for i, (timestamp, value) in enumerate(zip(timestamps, values, strict=False)):
            confidence_lower = None
            confidence_upper = None

            if confidence_intervals and i < len(confidence_intervals):
                confidence_lower, confidence_upper = confidence_intervals[i]

            data_points.append(
                TimePoint(
                    timestamp=timestamp,
                    value=value,
                    confidence_lower=confidence_lower,
                    confidence_upper=confidence_upper,
                )
            )

        return cls(data=data_points, frequency=frequency, metadata={"source": "simple_list"})
